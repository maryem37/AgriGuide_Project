"""Chargement de la configuration de l'agent depuis les variables d'environnement (.env).

Centralise les paramètres : clés API (Mistral, recherche web), URL/collection Qdrant, etc.
"""

from functools import lru_cache

from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    """Paramètres de configuration de l'application, lus depuis `.env`."""

    model_config = SettingsConfigDict(env_file=".env", env_file_encoding="utf-8", extra="ignore")

    mistral_api_key: str
    qdrant_url: str
    qdrant_api_key: str
    qdrant_collection_name: str
    web_search_api_key: str = ""
    vectorstore_path: str = "data/vectorstore"


@lru_cache
def get_settings() -> Settings:
    """Retourne l'instance (mise en cache) de configuration de l'application."""
    return Settings()
