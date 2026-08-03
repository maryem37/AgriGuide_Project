"""
Retrieve market evidence from the local vector store (Mistral embeddings).
"""

from __future__ import annotations

from pathlib import Path

from app.market_intelligence.rag.embeddings import embed_query
from app.market_intelligence.rag.local_store import LocalVectorStore

STORE_DIR = Path(__file__).resolve().parent / "vector_store"
COLLECTION_NAME = "agri_market_data"
CANDIDATE_MULTIPLIER = 4

_store: LocalVectorStore | None = None


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

    # Cosine distance already ranks relevance; expose as rerank_score = 1 - distance
    hits = []
    for text, meta, dist in zip(documents, metadatas, distances):
        hits.append(
            {
                "text": text,
                "metadata": meta,
                "distance": dist,
                "rerank_score": float(1.0 - dist),
            }
        )
    hits.sort(key=lambda h: h["rerank_score"], reverse=True)
    return hits[:top_k]
