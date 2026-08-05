"""
Researcher agent.

Given a crop name (and optional angle), this agent:
1. Asks the LLM to plan a small set of high-quality search queries.
2. Runs those queries against the academic search aggregator (Semantic
   Scholar + CrossRef) and the general web search provider (Tavily/Serper).
3. Returns a deduplicated list of SearchResult objects, ready to be fed
   into the extractor agent.

This agent does NOT extract facts and does NOT write to the knowledge
base - it only gathers candidate sources.
"""
from __future__ import annotations

from typing import Optional

from config.logging_config import get_logger
from config.settings import settings
from models import SearchResult
from prompts.research_prompts import RESEARCH_PLANNING_SYSTEM_PROMPT, RESEARCH_PLANNING_USER_PROMPT
from services.academic_search_service import AcademicSearchAggregator
from services.llm_service import LLMService, LLMServiceError, get_llm_service
from services.tracing_service import log_metadata, traced
from services.web_search_service import WebSearchError, WebSearchProvider, get_web_search_provider

logger = get_logger(__name__)


class ResearcherAgent:
    """Plans search queries and gathers candidate sources for a crop."""

    def __init__(
        self,
        llm_service: Optional[LLMService] = None,
        web_search_provider: Optional[WebSearchProvider] = None,
        academic_search: Optional[AcademicSearchAggregator] = None,
    ) -> None:
        self.llm_service = llm_service or get_llm_service()
        self.web_search_provider = web_search_provider or get_web_search_provider()
        self.academic_search = academic_search or AcademicSearchAggregator()

    @traced(name="plan_search_queries")
    def plan_queries(self, crop: str, angle: str = "", max_queries: Optional[int] = None) -> list[str]:
        """Ask the LLM to generate a small set of targeted search queries."""
        max_queries = max_queries or settings.max_search_queries_per_crop
        user_prompt = RESEARCH_PLANNING_USER_PROMPT.format(crop=crop, angle=angle, max_queries=max_queries)
        try:
            result = self.llm_service.complete_json(RESEARCH_PLANNING_SYSTEM_PROMPT, user_prompt)
        except LLMServiceError as e:
            logger.error("Query planning failed for crop '%s': %s. Falling back to a single default query.", crop, e)
            return [f"{crop} agricultural waste byproducts valorization"]

        if not isinstance(result, list):
            logger.warning("Query planner returned non-list output for crop '%s'; using fallback query.", crop)
            return [f"{crop} agricultural waste byproducts valorization"]

        queries = [str(q).strip() for q in result if str(q).strip()]
        return queries[:max_queries] or [f"{crop} agricultural waste byproducts valorization"]

    @traced(name="gather_sources", run_type="retriever")
    def gather_sources(self, crop: str, angle: str = "", max_queries: Optional[int] = None) -> list[SearchResult]:
        """
        Full research pass for a crop: plan queries, run them against both
        academic and web search, and return a deduplicated result list.
        """
        queries = self.plan_queries(crop, angle=angle, max_queries=max_queries)
        logger.info("Researcher generated %d queries for crop '%s': %s", len(queries), crop, queries)

        all_results: list[SearchResult] = []
        for query in queries:
            all_results.extend(self._safe_academic_search(query))
            all_results.extend(self._safe_web_search(query))

        deduped = _dedupe_search_results(all_results)
        logger.info(
            "Researcher gathered %d unique sources (from %d raw results) for crop '%s'.",
            len(deduped),
            len(all_results),
            crop,
        )
        log_metadata(
            crop=crop,
            queries_run=len(queries),
            raw_results=len(all_results),
            unique_sources=len(deduped),
        )
        return deduped

    def _safe_academic_search(self, query: str) -> list[SearchResult]:
        try:
            return self.academic_search.search(query, max_results_per_provider=settings.max_sources_per_query)
        except Exception as e:  # noqa: BLE001
            logger.warning("Academic search failed for query '%s': %s", query, e)
            return []

    def _safe_web_search(self, query: str) -> list[SearchResult]:
        try:
            return self.web_search_provider.search(query, max_results=settings.max_sources_per_query)
        except WebSearchError as e:
            logger.warning("Web search failed for query '%s': %s", query, e)
            return []
        except Exception as e:  # noqa: BLE001
            logger.warning("Unexpected web search error for query '%s': %s", query, e)
            return []


def _dedupe_search_results(results: list[SearchResult]) -> list[SearchResult]:
    seen: set[str] = set()
    out = []
    for r in results:
        key = r.doi or r.url or r.title
        if not key or key in seen:
            continue
        seen.add(key)
        out.append(r)
    return out
