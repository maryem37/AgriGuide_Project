"""Service de recherche par mots-clés (BM25).

Fournit la partie "recherche lexicale" du RAG hybride. La collection Qdrant
`agricultural_knowledge` stocke un vecteur épars natif ("text-sparse", modifier
IDF) généré avec le modèle BM25 de fastembed : on réutilise ce même modèle pour
vectoriser les requêtes, afin qu'elles soient comparables aux documents.
"""

from functools import lru_cache

from fastembed import SparseTextEmbedding
from qdrant_client import models

BM25_SPARSE_MODEL = "Qdrant/bm25"


@lru_cache
def get_bm25_model() -> SparseTextEmbedding:
    """Retourne le modèle d'embedding épars BM25 (mis en cache)."""
    return SparseTextEmbedding(model_name=BM25_SPARSE_MODEL)


def embed_query_sparse(text: str) -> models.SparseVector:
    """Vectorise une requête utilisateur en un vecteur épars de type BM25."""
    model = get_bm25_model()
    embedding = next(model.query_embed(text))
    return models.SparseVector(
        indices=embedding.indices.tolist(),
        values=embedding.values.tolist(),
    )
