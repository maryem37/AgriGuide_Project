"""
Embedding service, wrapping a sentence-transformers BGE model.

Kept as a thin, swappable wrapper so the vector store's embedding step (or any
future vector store) can be backed by a different model/provider without
touching the rest of the codebase.
"""
from __future__ import annotations

from typing import Optional

from config.logging_config import get_logger
from config.settings import settings

logger = get_logger(__name__)


class EmbeddingService:
    """Lazy-loaded sentence-transformers embedding wrapper."""

    def __init__(self, model_name: Optional[str] = None) -> None:
        self.model_name = model_name or settings.embedding_model_name
        self._model = None

    def _load(self):
        if self._model is None:
            logger.info("Loading embedding model '%s' (first use, may take a moment)...", self.model_name)
            from sentence_transformers import SentenceTransformer

            self._model = SentenceTransformer(self.model_name)
        return self._model

    def embed(self, texts: list[str]) -> list[list[float]]:
        """Embed a batch of texts, returning one vector per input string."""
        if not texts:
            return []
        model = self._load()
        # BGE models recommend normalizing embeddings for cosine similarity
        vectors = model.encode(texts, normalize_embeddings=True, show_progress_bar=False)
        return vectors.tolist()

    def embed_one(self, text: str) -> list[float]:
        return self.embed([text])[0]


_embedding_service_singleton: Optional[EmbeddingService] = None


def get_embedding_service() -> EmbeddingService:
    """Return a process-wide singleton so the model is loaded only once."""
    global _embedding_service_singleton
    if _embedding_service_singleton is None:
        _embedding_service_singleton = EmbeddingService()
    return _embedding_service_singleton
