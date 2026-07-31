"""Service d'accès au vector store Qdrant.

Gère la connexion au cluster Qdrant (Cloud) et l'accès à la collection
`agricultural_knowledge`, déjà peuplée avec les textes réglementaires
embeddés (vecteur dense "text-dense" + vecteur épars "text-sparse").
"""

from functools import lru_cache

from qdrant_client import QdrantClient

from app.config.settings import get_settings


@lru_cache
def get_vectorstore() -> QdrantClient:
    """Retourne le client Qdrant (mis en cache) connecté au cluster configuré."""
    settings = get_settings()
    return QdrantClient(url=settings.qdrant_url, api_key=settings.qdrant_api_key)


def get_collection_name() -> str:
    """Retourne le nom de la collection Qdrant à interroger."""
    return get_settings().qdrant_collection_name
