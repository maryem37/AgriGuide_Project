"""
General web search service abstraction, with Tavily and Serper implementations.

This complements academic_search_service.py: web search casts a wider net
(agricultural extension sites, industry reports, government publications)
that academic APIs alone would miss, while academic search targets
peer-reviewed rigor. The researcher agent uses both.
"""
from __future__ import annotations

from abc import ABC, abstractmethod
from typing import Optional

import requests

from config.logging_config import get_logger
from config.settings import settings
from models import SearchResult, SourceType

logger = get_logger(__name__)


class WebSearchError(Exception):
    """Raised when a web search provider call fails."""


class WebSearchProvider(ABC):
    """Abstract interface every general web search provider must implement."""

    @abstractmethod
    def search(self, query: str, max_results: Optional[int] = None) -> list[SearchResult]:
        raise NotImplementedError


class TavilySearchProvider(WebSearchProvider):
    """Tavily API implementation. https://docs.tavily.com/"""

    API_URL = "https://api.tavily.com/search"

    def __init__(self, api_key: Optional[str] = None) -> None:
        self.api_key = api_key or settings.tavily_api_key
        if not self.api_key:
            logger.warning("TAVILY_API_KEY is not set. TavilySearchProvider calls will fail until configured.")

    def search(self, query: str, max_results: Optional[int] = None) -> list[SearchResult]:
        if not self.api_key:
            raise WebSearchError("TAVILY_API_KEY is not configured.")
        max_results = max_results or settings.web_search_max_results
        try:
            resp = requests.post(
                self.API_URL,
                json={
                    "api_key": self.api_key,
                    "query": query,
                    "max_results": max_results,
                    "search_depth": "advanced",
                    "include_answer": False,
                },
                timeout=20,
            )
            resp.raise_for_status()
            data = resp.json()
        except requests.RequestException as e:
            logger.error("Tavily search failed for query '%s': %s", query, e)
            raise WebSearchError(str(e)) from e

        results = []
        for item in data.get("results", []):
            results.append(
                SearchResult(
                    source_type=SourceType.WEB_PAGE,
                    title=item.get("title", ""),
                    url=item.get("url"),
                    snippet=item.get("content", ""),
                    full_text=item.get("raw_content"),
                )
            )
        return results


class SerperSearchProvider(WebSearchProvider):
    """Serper.dev API implementation (Google Search wrapper). https://serper.dev/"""

    API_URL = "https://google.serper.dev/search"

    def __init__(self, api_key: Optional[str] = None) -> None:
        self.api_key = api_key or settings.serper_api_key
        if not self.api_key:
            logger.warning("SERPER_API_KEY is not set. SerperSearchProvider calls will fail until configured.")

    def search(self, query: str, max_results: Optional[int] = None) -> list[SearchResult]:
        if not self.api_key:
            raise WebSearchError("SERPER_API_KEY is not configured.")
        max_results = max_results or settings.web_search_max_results
        try:
            resp = requests.post(
                self.API_URL,
                headers={"X-API-KEY": self.api_key, "Content-Type": "application/json"},
                json={"q": query, "num": max_results},
                timeout=20,
            )
            resp.raise_for_status()
            data = resp.json()
        except requests.RequestException as e:
            logger.error("Serper search failed for query '%s': %s", query, e)
            raise WebSearchError(str(e)) from e

        results = []
        for item in data.get("organic", [])[:max_results]:
            results.append(
                SearchResult(
                    source_type=SourceType.WEB_PAGE,
                    title=item.get("title", ""),
                    url=item.get("link"),
                    snippet=item.get("snippet", ""),
                )
            )
        return results


def get_web_search_provider() -> WebSearchProvider:
    """Factory returning the configured web search provider."""
    if settings.web_search_provider == "tavily":
        return TavilySearchProvider()
    if settings.web_search_provider == "serper":
        return SerperSearchProvider()
    raise ValueError(
        f"Unknown web_search_provider '{settings.web_search_provider}'. Use 'tavily' or 'serper', "
        f"or implement a new WebSearchProvider subclass and register it here."
    )
