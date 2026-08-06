"""
Academic search service: Semantic Scholar + CrossRef.

Both APIs are free and do not strictly require an API key (Semantic
Scholar allows an optional key for higher rate limits; CrossRef asks only
for a polite "mailto" contact in the User-Agent for better rate limits).
These are the primary sources for peer-reviewed rigor, complementing the
general web search provider.
"""
from __future__ import annotations

from typing import Optional

import requests

from config.logging_config import get_logger
from config.settings import settings
from models import SearchResult, SourceType

logger = get_logger(__name__)


class AcademicSearchError(Exception):
    """Raised when an academic search API call fails."""


class SemanticScholarProvider:
    """https://api.semanticscholar.org/api-docs/graph"""

    API_URL = "https://api.semanticscholar.org/graph/v1/paper/search"
    FIELDS = "title,abstract,year,authors,externalIds,url"

    def __init__(self, api_key: Optional[str] = None) -> None:
        self.api_key = api_key or settings.semantic_scholar_api_key

    def search(self, query: str, max_results: Optional[int] = None) -> list[SearchResult]:
        max_results = max_results or settings.semantic_scholar_max_results
        headers = {"x-api-key": self.api_key} if self.api_key else {}
        try:
            resp = requests.get(
                self.API_URL,
                params={"query": query, "limit": max_results, "fields": self.FIELDS},
                headers=headers,
                timeout=20,
            )
            resp.raise_for_status()
            data = resp.json()
        except requests.RequestException as e:
            logger.error("Semantic Scholar search failed for query '%s': %s", query, e)
            raise AcademicSearchError(str(e)) from e

        results = []
        for item in data.get("data", []):
            authors = [a.get("name", "") for a in item.get("authors", []) if a.get("name")]
            external_ids = item.get("externalIds") or {}
            results.append(
                SearchResult(
                    source_type=SourceType.ACADEMIC_PAPER,
                    title=item.get("title", ""),
                    url=item.get("url"),
                    doi=external_ids.get("DOI"),
                    authors=authors,
                    published_year=item.get("year"),
                    snippet=item.get("abstract") or "",
                    full_text=item.get("abstract"),
                )
            )
        return results


class CrossRefProvider:
    """https://api.crossref.org/swagger-ui/index.html"""

    API_URL = "https://api.crossref.org/works"

    def __init__(self, mailto: Optional[str] = None) -> None:
        self.mailto = mailto or settings.crossref_mailto

    def search(self, query: str, max_results: Optional[int] = None) -> list[SearchResult]:
        max_results = max_results or settings.crossref_max_results
        params = {"query": query, "rows": max_results}
        headers = {}
        if self.mailto:
            headers["User-Agent"] = f"AgriWasteAgent/1.0 (mailto:{self.mailto})"
        try:
            resp = requests.get(self.API_URL, params=params, headers=headers, timeout=20)
            resp.raise_for_status()
            data = resp.json()
        except requests.RequestException as e:
            logger.error("CrossRef search failed for query '%s': %s", query, e)
            raise AcademicSearchError(str(e)) from e

        results = []
        for item in data.get("message", {}).get("items", []):
            title_list = item.get("title") or []
            title = title_list[0] if title_list else ""
            authors = []
            for a in item.get("author", []) or []:
                name = " ".join(filter(None, [a.get("given"), a.get("family")]))
                if name:
                    authors.append(name)
            year = None
            date_parts = (item.get("published") or {}).get("date-parts")
            if date_parts and date_parts[0]:
                year = date_parts[0][0]
            abstract = item.get("abstract", "")
            # CrossRef abstracts sometimes come wrapped in JATS XML tags
            abstract = _strip_jats_tags(abstract) if abstract else ""

            results.append(
                SearchResult(
                    source_type=SourceType.ACADEMIC_PAPER,
                    title=title,
                    url=item.get("URL"),
                    doi=item.get("DOI"),
                    authors=authors,
                    published_year=year,
                    snippet=abstract,
                    full_text=abstract or None,
                )
            )
        return results


def _strip_jats_tags(text: str) -> str:
    import re

    return re.sub(r"<[^>]+>", "", text).strip()


class AcademicSearchAggregator:
    """Runs a query against both academic providers and merges results."""

    def __init__(self) -> None:
        self.semantic_scholar = SemanticScholarProvider()
        self.crossref = CrossRefProvider()

    def search(self, query: str, max_results_per_provider: Optional[int] = None) -> list[SearchResult]:
        results: list[SearchResult] = []
        try:
            results.extend(self.semantic_scholar.search(query, max_results_per_provider))
        except AcademicSearchError:
            logger.warning("Semantic Scholar search failed for '%s', continuing with CrossRef only.", query)
        try:
            results.extend(self.crossref.search(query, max_results_per_provider))
        except AcademicSearchError:
            logger.warning("CrossRef search failed for '%s'.", query)
        return results
