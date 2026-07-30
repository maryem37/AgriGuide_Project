"""
Structure-aware chunking, embedding, filtered-then-semantic retrieval.
Uses Mistral Embed as the primary path, sent in small batches so no
single request can trip Mistral's per-request token limit; falls back
to a free self-hosted multilingual model for INDEXING only when
Mistral is genuinely unreachable. Retrieval never falls back silently,
since the Chroma collection's embedding dimensionality is fixed at
first insert (1024-dim for Mistral) — a 768-dim local query vector can
never match it, so a silent fallback there would always break, not
just degrade.

Ported as-is from the standalone `agri-advisor-parcelle` prototype.
"""
import sys
import uuid
import chromadb
from chromadb.config import Settings as ChromaSettings
from sentence_transformers import SentenceTransformer
from tenacity import retry, stop_after_attempt, wait_exponential, retry_if_exception
from app.config import settings
from app.models.schemas import RetrievedChunk

_client = chromadb.PersistentClient(
    path=settings.chroma_persist_dir,
    settings=ChromaSettings(anonymized_telemetry=False),
)
_collection = _client.get_or_create_collection(settings.chroma_collection)

_local_model: SentenceTransformer | None = None
_using_local_fallback = False  # tracks which embedding space is active this run

_MISTRAL_EMBED_BATCH_SIZE = 8


def _get_local_model() -> SentenceTransformer:
    global _local_model
    if _local_model is None:
        _local_model = SentenceTransformer(settings.local_embed_model)
    return _local_model


def _is_transient(exc: Exception) -> bool:
    """
    Retry errors that are likely to resolve on their own: rate limits,
    server-side 5xx, and network-level failures (dropped Wi-Fi, DNS
    hiccup, unreachable host). A 400 "bad request" (e.g. too many
    tokens) is a request-shape problem — retrying it is pointless.
    """
    msg = str(exc).lower()
    if "429" in msg or "rate limit" in msg:
        return True
    if any(code in msg for code in ("500", "502", "503", "504")):
        return True
    # Windows/socket-level connectivity errors don't carry HTTP codes
    network_signals = (
        "network is unreachable", "unreachable network", "winerror 10051",
        "connection reset", "connection refused", "connection aborted",
        "timed out", "timeout", "getaddrinfo failed", "name or service not known",
    )
    if any(sig in msg for sig in network_signals):
        return True
    return False


@retry(
    stop=stop_after_attempt(5),
    wait=wait_exponential(min=2, max=30),
    retry=retry_if_exception(_is_transient),
    reraise=True,
)
def _mistral_embed_call(texts: list[str]) -> list[list[float]]:
    from mistralai import Mistral
    client = Mistral(api_key=settings.mistral_api_key)
    resp = client.embeddings.create(model=settings.mistral_embed_model, inputs=texts)
    return [d.embedding for d in resp.data]


def _mistral_embed(texts: list[str]) -> list[list[float]]:
    results = []
    for i in range(0, len(texts), _MISTRAL_EMBED_BATCH_SIZE):
        batch = texts[i : i + _MISTRAL_EMBED_BATCH_SIZE]
        results.extend(_mistral_embed_call(batch))
    return results


def embed_texts_for_indexing(texts: list[str]) -> list[list[float]]:
    """
    Used when ADDING new chunks to the store. Safe to fall back to local
    here IF this is the very first data ever indexed (empty collection) —
    otherwise falling back mid-corpus still risks a dimension mismatch
    against what's already stored, so we warn loudly either way.
    """
    global _using_local_fallback

    if settings.mistral_api_key and not _using_local_fallback:
        try:
            return _mistral_embed(texts)
        except Exception as e:
            print(
                f"\n⚠️  WARNING: Mistral Embed failed after retries ({e}). "
                f"Switching to local fallback model for the REST of this run. "
                f"If the Chroma collection already has Mistral (1024-dim) embeddings, "
                f"this WILL cause a dimension mismatch — delete chroma_store/ and "
                f"re-ingest once Mistral is reachable again.\n",
                file=sys.stderr,
            )
            _using_local_fallback = True

    model = _get_local_model()
    return model.encode(texts, normalize_embeddings=True).tolist()


def embed_query_for_retrieval(text: str) -> list[float]:
    """
    Used when QUERYING the existing store. Never falls back to local —
    the collection's dimensionality is fixed at whatever embedded the
    first chunk (1024-dim, if Mistral built it), so a 768-dim local
    query vector can never match regardless of how it's produced.
    Retries harder, then raises a clear, actionable error instead of
    letting Chroma's internals throw an opaque dimension exception.
    """
    if not settings.mistral_api_key:
        raise RuntimeError(
            "No MISTRAL_API_KEY set, but retrieval requires the same embedding "
            "space the collection was built with (Mistral, 1024-dim). Set "
            "MISTRAL_API_KEY in .env to query this collection."
        )
    try:
        return _mistral_embed([text])[0]
    except Exception as e:
        raise RuntimeError(
            f"Could not reach Mistral Embed for retrieval after retries: {e}. "
            f"This is likely a network issue — check your connection and retry. "
            f"(Falling back to a different embedding model here would silently "
            f"break retrieval, since it wouldn't match the collection's stored "
            f"embedding dimensionality.)"
        ) from e


def chunk_document(text: str, source_document: str, metadata_defaults: dict | None = None) -> list[dict]:
    """
    Structure-aware-ish chunking: splits on markdown headings/paragraph
    breaks first, then packs sequential blocks up to chunk_max_tokens
    with overlap. For full PDF structural parsing, run documents through
    `unstructured` in scripts/ingest_rag_corpus.py before calling this —
    this function chunks already-extracted text/markdown.
    """
    metadata_defaults = metadata_defaults or {}
    blocks = [b.strip() for b in text.split("\n\n") if b.strip()]

    chunks, current, current_len = [], [], 0
    max_tok, min_tok = settings.chunk_max_tokens, settings.chunk_min_tokens

    def flush():
        if current:
            chunks.append(" ".join(current))

    for block in blocks:
        block_len = len(block.split())
        if current_len + block_len > max_tok and current_len >= min_tok:
            flush()
            overlap_words = " ".join(current).split()
            overlap_n = int(len(overlap_words) * settings.chunk_overlap_ratio)
            current = overlap_words[-overlap_n:] if overlap_n else []
            current_len = len(current)
        current.append(block)
        current_len += block_len
    flush()

    return [
        {
            "id": str(uuid.uuid4()),
            "text": c,
            "source_document": source_document,
            **metadata_defaults,
        }
        for c in chunks
    ]


def index_chunks(chunks: list[dict]) -> None:
    embeddings = embed_texts_for_indexing([c["text"] for c in chunks])
    _collection.add(
        ids=[c["id"] for c in chunks],
        documents=[c["text"] for c in chunks],
        embeddings=embeddings,
        metadatas=[
            {
                "source_document": c["source_document"],
                "crop": c.get("crop", ""),
                "region": c.get("region", ""),
                "topic": c.get("topic", ""),
            }
            for c in chunks
        ],
    )


def retrieve(
    query: str,
    crop_filter: str | None = None,
    region_filter: str | None = None,
    topic_filter: str | None = None,
    top_k: int | None = None,
) -> list[RetrievedChunk]:
    """Filter-then-semantic: metadata `where` narrows candidates before ranking."""
    conditions = []
    if crop_filter:
        conditions.append({"crop": crop_filter})
    if region_filter:
        conditions.append({"region": region_filter})
    if topic_filter:
        conditions.append({"topic": topic_filter})

    # chromadb 0.5.x requires a single top-level operator: a flat dict with
    # more than one key raises "Expected where to have exactly one operator".
    # A single condition can be passed as-is; two or more must be wrapped in $and.
    if not conditions:
        where = None
    elif len(conditions) == 1:
        where = conditions[0]
    else:
        where = {"$and": conditions}

    query_embedding = embed_query_for_retrieval(query)
    results = _collection.query(
        query_embeddings=[query_embedding],
        n_results=top_k or settings.retrieval_top_k,
        where=where,
    )

    out = []
    ids = results.get("ids", [[]])[0]
    docs = results.get("documents", [[]])[0]
    metas = results.get("metadatas", [[]])[0]
    dists = results.get("distances", [[]])[0]
    for i, doc, meta, dist in zip(ids, docs, metas, dists):
        out.append(
            RetrievedChunk(
                chunk_id=i,
                text=doc,
                source_document=meta.get("source_document", "unknown"),
                crop=meta.get("crop") or None,
                region=meta.get("region") or None,
                topic=meta.get("topic") or None,
                score=1 - dist,  # chroma returns distance; convert to similarity
            )
        )
    return out
