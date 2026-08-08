"""
One-off migration: push this service's Chroma vector store
(chroma_store/, built by scripts/ingest_rag_corpus.py) into Qdrant
Cloud, into the "Agricultural Advisor" collection.

Ported from the standalone `agri-advisor-parcelle` prototype (import
paths updated to the `app.*` package layout, run convention matching
the other scripts/ in this service). Mirrors the Government
Regulations feature's embed_to_qdrant.py (same hybrid shape: dense
"text-dense" + sparse "text-sparse", same Qdrant/bm25 sparse model) so
every collection in the cluster (agricultural_knowledge,
agriculture_regulations, Agricultural Advisor) stays queryable the
same way.

Key difference from that script: we do NOT re-call the Mistral Embed
API here. Every chunk in chroma_store/ was already embedded with
mistral-embed at ingest time (app/services/rag_service.py) — pulling
those 1024-dim vectors straight out of Chroma is free, instant, and
guarantees Qdrant holds the exact same vectors already used for local
retrieval. Only the sparse (BM25) side is computed fresh, since Chroma
never stored one.

Installation:
    pip install qdrant-client fastembed
    (both already added to requirements.txt)

.env variables needed (repo-root .env or backend/agent_agriculture/.env,
same lookup order as app/config.py):
    QDRANT_URL, QDRANT_API_KEY
    QDRANT_COLLECTION   (optional — defaults to "Agricultural Advisor")

Run from backend/agent_agriculture/:
    python -m scripts.push_to_qdrant
    python -m scripts.push_to_qdrant --batch-size 50
    python -m scripts.push_to_qdrant --dry-run
"""
from __future__ import annotations

import argparse
import time

from app.config import settings
from app.services.rag_service import _collection


def _get_sparse_model():
    from fastembed import SparseTextEmbedding
    return SparseTextEmbedding(model_name=settings.qdrant_sparse_model)


def load_chroma_chunks() -> dict:
    """Pulls every chunk out of the local Chroma store, WITH its already-
    computed embedding — no re-embedding needed for the dense side.
    `include` must be passed explicitly: chromadb doesn't return
    embeddings by default."""
    return _collection.get(limit=100000, include=["embeddings", "documents", "metadatas"])


def _upsert_with_retry(client, collection: str, points: list, max_retries: int = 4, backoff: float = 1.5) -> None:
    """Same retry pattern as the Regulations feature's script — Qdrant
    Cloud's default timeout can be too short for a batched write from
    some connections."""
    for attempt in range(1, max_retries + 1):
        try:
            client.upsert(collection_name=collection, points=points)
            return
        except Exception as exc:
            if attempt == max_retries:
                raise
            wait = backoff * attempt
            print(f"Qdrant upsert failed ({exc!r}), retrying in {wait:.0f}s ({attempt}/{max_retries})...")
            time.sleep(wait)


def push_to_qdrant(batch_size: int = 32, collection: str | None = None, dry_run: bool = False) -> int:
    from qdrant_client import QdrantClient
    from qdrant_client.models import Distance, PointStruct, SparseVector, SparseVectorParams, VectorParams

    if not settings.qdrant_url or not settings.qdrant_api_key:
        raise RuntimeError("QDRANT_URL / QDRANT_API_KEY missing from .env")

    collection = collection or settings.qdrant_collection

    data = load_chroma_chunks()
    ids = data.get("ids", [])
    embeddings = data.get("embeddings", [])
    documents = data.get("documents", [])
    metadatas = data.get("metadatas", [])

    if not ids:
        print("chroma_store/ is empty — nothing to push. Run `python -m scripts.ingest_rag_corpus` first.")
        return 0

    # Every point must be qdrant_dense_dim (1024) to match the
    # collection's existing "text-dense" config — flag (don't silently
    # push) any chunk that was indexed via the local fallback model
    # instead (768-dim), since a mixed-dimension push would corrupt
    # the collection rather than just degrading one point.
    bad_idx = [i for i, e in enumerate(embeddings) if len(e) != settings.qdrant_dense_dim]
    if bad_idx:
        sample = [ids[i] for i in bad_idx[:5]]
        print(
            f"⚠️  {len(bad_idx)} chunk(s) have embeddings of the wrong dimension "
            f"(expected {settings.qdrant_dense_dim} — likely indexed via the local "
            f"fallback model, not mistral-embed, e.g. because MISTRAL_API_KEY was "
            f"unset during that ingest run). Skipping them: {sample}"
            f"{' ...' if len(bad_idx) > 5 else ''}\n"
            f"   Re-ingest those source documents with a working MISTRAL_API_KEY, "
            f"then re-run this script, if you want them included."
        )
    keep = [i for i in range(len(ids)) if i not in set(bad_idx)]

    print(f"{len(keep)}/{len(ids)} chunks ready to push to Qdrant collection '{collection}'.")
    if dry_run:
        print("[DRY RUN] Nothing written.")
        return 0

    client = QdrantClient(url=settings.qdrant_url, api_key=settings.qdrant_api_key, timeout=settings.qdrant_timeout_seconds)
    if not client.collection_exists(collection):
        # Shouldn't normally trigger — "Agricultural Advisor" already
        # exists in the cluster with this exact vector config — but
        # kept so the script also works against a fresh cluster.
        print(f"Collection '{collection}' does not exist yet — creating it.")
        client.create_collection(
            collection,
            vectors_config={
                settings.qdrant_dense_vector_name: VectorParams(
                    size=settings.qdrant_dense_dim, distance=Distance.COSINE
                )
            },
            sparse_vectors_config={settings.qdrant_sparse_vector_name: SparseVectorParams()},
        )

    sparse_model = _get_sparse_model()

    total = 0
    for start in range(0, len(keep), batch_size):
        batch_idx = keep[start : start + batch_size]
        texts = [documents[i] for i in batch_idx]
        sparse_vecs = list(sparse_model.embed(texts))

        points = [
            PointStruct(
                id=ids[i],  # already a real UUID (uuid.uuid4() at ingest time, see rag_service.chunk_document) — usable as-is, no re-derivation needed
                vector={
                    settings.qdrant_dense_vector_name: embeddings[i],
                    settings.qdrant_sparse_vector_name: SparseVector(
                        indices=sv.indices.tolist(), values=sv.values.tolist()
                    ),
                },
                payload={
                    "text": documents[i],
                    **(metadatas[i] or {}),  # source_document, crop, region, topic (+ title/url once Tier 1's backfill has run)
                },
            )
            for i, sv in zip(batch_idx, sparse_vecs)
        ]
        _upsert_with_retry(client, collection, points)
        total += len(points)
        print(f"{total}/{len(keep)} chunks indexed...")

    print(f"\nDone. {total} chunks indexed into Qdrant collection '{collection}'.")
    return total


def main() -> None:
    ap = argparse.ArgumentParser(description="Push chroma_store/ into Qdrant (Agricultural Advisor collection).")
    ap.add_argument("--batch-size", type=int, default=32)
    ap.add_argument(
        "--collection", default=None,
        help=f"Defaults to settings.qdrant_collection ({settings.qdrant_collection!r}).",
    )
    ap.add_argument("--dry-run", action="store_true", help="Show what would be pushed without writing to Qdrant.")
    args = ap.parse_args()
    push_to_qdrant(batch_size=args.batch_size, collection=args.collection, dry_run=args.dry_run)


if __name__ == "__main__":
    main()
