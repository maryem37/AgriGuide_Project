"""Schémas Pydantic pour les résultats de recherche web (aides et réglementations récentes)."""

from pydantic import BaseModel


class WebSearchResult(BaseModel):
    """Un résultat de recherche web (aide, procédure, actualité réglementaire)."""

    title: str
    url: str
    source: str
    snippet: str
    published_date: str | None = None


class WebSearchResponse(BaseModel):
    """Ensemble des résultats retournés pour une requête de recherche web."""

    query: str
    results: list[WebSearchResult]
