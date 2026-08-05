"""
Knowledge base orchestrator agent.

This is the agent that ties everything together: it runs the researcher
to gather sources, the extractor to pull structured facts from each
source, the validator to clean/normalize/reject bad entries, and then
synchronizes the result into both canonical_knowledge.json (via
StorageService) and Qdrant (via VectorStoreService).

This is the module the UI/CLI calls to "build knowledge for a crop".
"""
from __future__ import annotations

from concurrent.futures import ThreadPoolExecutor, as_completed
from datetime import datetime, timezone
from typing import Callable, Optional

from agents.extractor import ExtractorAgent
from agents.parser import PDFParserAgent
from agents.researcher import ResearcherAgent
from agents.validator import ValidationError, ValidatorAgent
from config.logging_config import get_logger
from config.settings import settings
from models import Crop, ExtractionResult, ExtractionStatus, KnowledgeBase, SearchResult, Waste
from services.storage_service import StorageService, get_storage_service
from services.tracing_service import log_metadata, traced
from services.vector_store_service import VectorStoreService, get_vector_store

logger = get_logger(__name__)

ProgressCallback = Callable[[str, float], None]  # (message, progress_fraction_0_to_1)


def _build_batches(
    sources: list[SearchResult], batch_size: int, max_chars: int
) -> list[list[SearchResult]]:
    """
    Group sources into batches bounded by BOTH count and character budget.

    A fixed count alone doesn't work once full-text retrieval is on: six
    abstracts fit comfortably in one prompt, six full articles do not. The
    character budget keeps prompts within the model's context regardless of
    what the sources turned out to be. A single oversized source still gets
    its own batch rather than being dropped.
    """
    if batch_size <= 1:
        return [[s] for s in sources]

    batches: list[list[SearchResult]] = []
    current: list[SearchResult] = []
    current_chars = 0

    for source in sources:
        length = len(source.full_text or source.snippet or "")
        if current and (len(current) >= batch_size or current_chars + length > max_chars):
            batches.append(current)
            current, current_chars = [], 0
        current.append(source)
        current_chars += length

    if current:
        batches.append(current)
    return batches


class ResearchSummary:
    """Summary of a single research-and-sync pass, for UI display."""

    def __init__(self, crop_name: str) -> None:
        self.crop_name = crop_name
        self.sources_found: int = 0
        self.sources_used: int = 0
        self.wastes_added_or_updated: int = 0
        self.rejected_extractions: int = 0
        self.errors: list[str] = []

    def as_dict(self) -> dict:
        return {
            "crop_name": self.crop_name,
            "sources_found": self.sources_found,
            "sources_used": self.sources_used,
            "wastes_added_or_updated": self.wastes_added_or_updated,
            "rejected_extractions": self.rejected_extractions,
            "errors": self.errors,
        }


class KnowledgeBaseAgent:
    """Orchestrates research -> extraction -> validation -> synchronized storage."""

    def __init__(
        self,
        researcher: Optional[ResearcherAgent] = None,
        extractor: Optional[ExtractorAgent] = None,
        validator: Optional[ValidatorAgent] = None,
        storage: Optional[StorageService] = None,
        vector_store: Optional[VectorStoreService] = None,
    ) -> None:
        self.researcher = researcher or ResearcherAgent()
        self.extractor = extractor or ExtractorAgent()
        self.validator = validator or ValidatorAgent()
        self.storage = storage or get_storage_service()
        self.vector_store = vector_store or get_vector_store()
        self.pdf_parser = PDFParserAgent()

    @traced(name="sync_from_sources")
    def sync_from_sources(
        self,
        crop_name: str,
        sources: list[SearchResult],
        progress_cb: Optional[ProgressCallback] = None,
        max_workers: int = settings.llm_max_parallel_extractions,
    ) -> ResearchSummary:
        """
        Shared core: run extraction+validation+sync over an already-gathered
        list of sources. Used by both the autonomous research path
        (research_and_sync_crop) and the secondary PDF-upload path
        (sync_from_pdf).
        """
        summary = ResearchSummary(crop_name)

        def report(msg: str, frac: float) -> None:
            logger.info(msg)
            if progress_cb:
                progress_cb(msg, frac)

        summary.sources_found = len(sources)
        if not sources:
            summary.errors.append("No sources to process.")
            return summary

        kb = self.storage.load()
        target_crop: Optional[Crop] = None

        # The cheap pre-filter runs before any LLM call, so obviously-thin
        # sources never cost a request. Every source that passes it is still
        # analyzed -- only the count of *calls* changes, via batching below.
        usable = [s for s in sources if self.extractor.is_worth_extracting(s)]
        batches = _build_batches(usable, settings.extraction_batch_size, settings.extraction_batch_max_chars)
        total_batches = len(batches)

        # Extraction dominates runtime and each batch is one Mistral call;
        # run batches concurrently (bounded by llm_max_parallel_extractions
        # to stay under the provider's rate limit). Merging into `kb` below
        # stays sequential (shared mutable state, and it's cheap compared to
        # the LLM calls).
        batch_results: dict[str, ExtractionResult] = {}
        completed = 0
        with ThreadPoolExecutor(max_workers=max(1, max_workers)) as pool:
            future_to_batch = {
                pool.submit(self.extractor.extract_batch, batch, crop_name): batch for batch in batches
            }
            for future in as_completed(future_to_batch):
                batch = future_to_batch[future]
                try:
                    batch_results.update(future.result())
                except Exception as e:  # noqa: BLE001
                    logger.error("Batch extraction raised unexpectedly for %d source(s): %s", len(batch), e)
                    for source in batch:
                        batch_results[self.extractor._source_key(source)] = ExtractionResult(
                            status=ExtractionStatus.UNKNOWN, message=str(e)
                        )
                completed += 1
                frac = 0.1 + 0.6 * (completed / max(total_batches, 1))
                report(f"Extracted batch {completed}/{total_batches} ({len(batch)} sources)...", frac)

        total = len(usable)
        for i, source in enumerate(usable):
            frac = 0.7 + 0.1 * ((i + 1) / max(total, 1))
            report(f"Merging source {i + 1}/{total}: {source.title[:60]}...", frac)

            extraction = batch_results.get(self.extractor._source_key(source))
            if extraction is None or extraction.status != ExtractionStatus.SUCCESS or not extraction.wastes:
                continue

            try:
                cleaned = self.validator.validate_and_normalize(extraction)
            except ValidationError as e:
                summary.rejected_extractions += 1
                summary.errors.append(str(e))
                continue

            if not cleaned.wastes:
                continue

            summary.sources_used += 1
            summary.wastes_added_or_updated += len(cleaned.wastes)

            crop = Crop(
                name=cleaned.crop,
                canonical_name=cleaned.crop,
                scientific_name=cleaned.scientific_name,
                aliases=cleaned.aliases,
                wastes=cleaned.wastes,
            )
            if not self.validator.validate_crop_for_knowledge_base(crop):
                summary.rejected_extractions += 1
                continue

            target_crop = kb.upsert_crop(crop)

        if target_crop is None:
            summary.errors.append("No source yielded validated, extractable waste data.")
            return summary

        target_crop.last_research_at = datetime.now(timezone.utc).isoformat()
        report("Saving knowledge base...", 0.85)
        self.storage.save(kb)

        report("Syncing vector store...", 0.92)
        try:
            self.vector_store.upsert_crop(target_crop)
        except Exception as e:  # noqa: BLE001
            logger.error("Vector store sync failed for '%s': %s", crop_name, e)
            summary.errors.append(f"Vector store sync failed: {e}")

        report(f"Done: {summary.wastes_added_or_updated} waste entries synced for '{crop_name}'.", 1.0)
        log_metadata(
            crop=crop_name,
            sources_found=summary.sources_found,
            sources_used=summary.sources_used,
            wastes_synced=summary.wastes_added_or_updated,
            rejected_extractions=summary.rejected_extractions,
            errors=len(summary.errors),
        )
        return summary

    def sync_from_pdf(
        self,
        pdf_path: str,
        crop_hint: str,
        title_hint: str = "",
        progress_cb: Optional[ProgressCallback] = None,
    ) -> ResearchSummary:
        """Secondary path: parse an uploaded PDF and run it through the same pipeline."""
        if progress_cb:
            progress_cb(f"Parsing PDF '{pdf_path}'...", 0.02)
        sources = self.pdf_parser.parse(pdf_path, title_hint=title_hint)
        return self.sync_from_sources(crop_hint, sources, progress_cb=progress_cb)

    @traced(name="research_and_sync_crop")
    def research_and_sync_crop(
        self,
        crop_name: str,
        angle: str = "",
        max_queries: Optional[int] = None,
        progress_cb: Optional[ProgressCallback] = None,
    ) -> ResearchSummary:
        """
        Full pipeline for one crop: gather sources, extract, validate,
        merge into the knowledge base, sync to the vector store.
        """
        summary = ResearchSummary(crop_name)

        def report(msg: str, frac: float) -> None:
            logger.info(msg)
            if progress_cb:
                progress_cb(msg, frac)

        report(f"Planning research for '{crop_name}'...", 0.05)
        sources = self.researcher.gather_sources(crop_name, angle=angle, max_queries=max_queries)

        if not sources:
            summary.sources_found = 0
            summary.errors.append("No sources found from web or academic search.")
            report(f"No sources found for '{crop_name}'.", 1.0)
            return summary

        return self.sync_from_sources(crop_name, sources, progress_cb=progress_cb)

    def get_knowledge_base(self) -> KnowledgeBase:
        return self.storage.load()

    def get_crop(self, crop_name: str) -> Optional[Crop]:
        return self.storage.load().find_crop(crop_name)

    def needs_refresh(self, crop: Crop, freshness_days: int) -> bool:
        if crop.last_research_at is None:
            return True
        try:
            last = datetime.fromisoformat(crop.last_research_at)
        except ValueError:
            return True
        age_days = (datetime.now(timezone.utc) - last).days
        return age_days > freshness_days
