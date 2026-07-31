"""Service d'embeddings denses via le modèle Mistral (mistral-embed).

Fournit une interface unique pour vectoriser les requêtes utilisées par le
retriever sémantique. Le modèle produit des vecteurs de dimension 1024,
compatibles avec le vecteur nommé "text-dense" de la collection Qdrant.
"""

from functools import lru_cache

from mistralai.client import Mistral

from app.config.settings import get_settings

MISTRAL_EMBED_MODEL = "mistral-embed"


@lru_cache
def get_embedding_client() -> Mistral:
    """Retourne un client Mistral (mis en cache) pour générer des embeddings."""
    settings = get_settings()
    return Mistral(api_key=settings.mistral_api_key)


def embed_query(text: str) -> list[float]:
    """Vectorise une requête utilisateur en un embedding dense (dimension 1024)."""
    client = get_embedding_client()
    response = client.embeddings.create(model=MISTRAL_EMBED_MODEL, inputs=[text])
    return response.data[0].embedding
