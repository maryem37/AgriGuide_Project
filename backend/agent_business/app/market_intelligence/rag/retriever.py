"""
Retrieve market evidence from the local vector store (Mistral embeddings).
"""

from __future__ import annotations

from pathlib import Path
import re
import unicodedata

from app.market_intelligence.rag.embeddings import embed_query
from app.market_intelligence.rag.local_store import LocalVectorStore

STORE_DIR = Path(__file__).resolve().parent / "vector_store"
COLLECTION_NAME = "agri_market_data"
CANDIDATE_MULTIPLIER = 4

_store: LocalVectorStore | None = None


def _tokens(text: str) -> set[str]:
    normalized = unicodedata.normalize("NFKD", text).encode("ascii", "ignore").decode("ascii")
    return {
        token
        for token in re.findall(r"[a-z0-9]{3,}", normalized.lower())
        if token not in {"avec", "pour", "dans", "des", "les", "une"}
    }


def _lexical_score(query: str, document: str) -> float:
    query_tokens = _tokens(query)
    if not query_tokens:
        return 0.0
    return len(query_tokens & _tokens(document)) / len(query_tokens)


def _get_store() -> LocalVectorStore:
    global _store
    if _store is None:
        _store = LocalVectorStore(STORE_DIR, COLLECTION_NAME)
    return _store


def chroma_available() -> bool:
    """True if a usable collection already exists on disk (compat name)."""
    try:
        store = _get_store()
        return store.exists() and store.count() > 0
    except Exception:
        return False


def retrieve(query: str, top_k: int = 5, where: dict | None = None) -> list[dict]:
    """
    Vector search over indexed FranceAgriMer / Agreste chunks.
    Returns [{text, metadata, distance, rerank_score}, ...]
    """
    store = _get_store()
    if not store.exists():
        raise RuntimeError(
            f"Collection '{COLLECTION_NAME}' not found. "
            "Run: python -m app.market_intelligence.rag.ingest"
        )

    query_embedding = embed_query(query)
    candidate_k = max(top_k * CANDIDATE_MULTIPLIER, top_k)
    documents, metadatas, distances = store.query(
        query_embedding, n_results=candidate_k, where=where
    )

    if not documents:
        return []

    # Deterministic hybrid reranking: semantic cosine remains primary and
    # lexical crop/market-term overlap prevents generic PDFs from dominating.
    hits = []
    for text, meta, dist in zip(documents, metadatas, distances):
        semantic_score = max(0.0, min(1.0, 1.0 - dist))
        lexical_score = _lexical_score(query, text)
        rerank_score = 0.75 * semantic_score + 0.25 * lexical_score
        hits.append(
            {
                "text": text,
                "metadata": meta,
                "distance": dist,
                "semantic_score": round(semantic_score, 6),
                "lexical_score": round(lexical_score, 6),
                "rerank_score": round(rerank_score, 6),
            }
        )
    hits.sort(key=lambda h: h["rerank_score"], reverse=True)
    return hits[:top_k]
