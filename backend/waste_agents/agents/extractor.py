"""
Extractor agent.

Runs the extraction LLM prompt against a single SearchResult (an academic
abstract or a web page snippet), parses the JSON output, and builds
strongly-typed Crop/Waste model instances with proper Reference objects
attached to every waste. Validation and normalization beyond what the
prompt already enforces happens in agents/validator.py.
"""
from __future__ import annotations

from typing import Optional

from config.logging_config import get_logger
from config.settings import settings
from models import (
    Application,
    Composition,
    EvidenceSource,
    EvidenceStrength,
    ExtractionResult,
    ExtractionStatus,
    Reference,
    SearchResult,
    Transformation,
    Waste,
)
from prompts.extraction_prompts import (
    BATCH_EXTRACTION_SYSTEM_PROMPT,
    BATCH_EXTRACTION_USER_PROMPT,
    BATCH_PASSAGE_TEMPLATE,
    EXTRACTION_SYSTEM_PROMPT,
    EXTRACTION_USER_PROMPT,
)
from services.llm_service import LLMService, LLMServiceError, get_llm_service
from services.tracing_service import log_metadata, traced

logger = get_logger(__name__)


class ExtractorAgent:
    """Extracts structured Waste knowledge from a single source passage."""

    def __init__(self, llm_service: Optional[LLMService] = None) -> None:
        self.llm_service = llm_service or get_llm_service()

    def is_worth_extracting(self, source: SearchResult) -> bool:
        """
        Cheap pre-filter, no LLM call.

        A research pass costs one LLM call per source, so discarding
        hopeless sources in plain Python is the single cheapest speed-up
        available. Only obviously-unusable sources are dropped: anything
        borderline still goes to the model.
        """
        text = (source.full_text or source.snippet or "").strip()
        if len(text) < settings.extraction_min_source_chars:
            logger.debug("Skipping '%s': only %d chars of text.", source.title[:60], len(text))
            return False
        return True

    @traced(name="extract_from_source")
    def extract_from_source(self, source: SearchResult, requested_crop: str = "") -> ExtractionResult:
        """
        Extract structured knowledge from one SearchResult. Returns an
        ExtractionResult with status=UNKNOWN and empty wastes if nothing
        reliable could be extracted (never raises for "no data found").
        """
        text = source.full_text or source.snippet
        if not text or len(text.strip()) < 40:
            logger.debug("Source '%s' has insufficient text (<40 chars), skipping extraction.", source.title)
            return ExtractionResult(status=ExtractionStatus.UNKNOWN, message="Source text too short to extract from.")

        user_prompt = EXTRACTION_USER_PROMPT.format(
            title=source.title or "",
            authors=", ".join(source.authors) or "Unknown",
            published_year=source.published_year or "Unknown",
            url=source.url or "",
            doi=source.doi or "",
            source_type=source.source_type.value,
            text=text,
        )

        try:
            raw = self.llm_service.complete_json(EXTRACTION_SYSTEM_PROMPT, user_prompt)
        except LLMServiceError as e:
            logger.error("Extraction failed for source '%s': %s", source.title, e)
            return ExtractionResult(status=ExtractionStatus.UNKNOWN, message=f"Extraction call failed: {e}")

        if not isinstance(raw, dict):
            logger.warning("Extractor returned non-dict JSON for source '%s'.", source.title)
            return ExtractionResult(status=ExtractionStatus.UNKNOWN, message="Extractor returned malformed output.")

        result = self._build_extraction_result(raw, source, requested_crop)
        log_metadata(
            source_title=source.title[:120],
            source_type=source.source_type.value,
            input_chars=len(text),
            crop_extracted=result.crop,
            wastes_extracted=len(result.wastes),
            status=result.status.value,
        )
        return result

    @traced(name="extract_batch")
    def extract_batch(
        self, sources: list[SearchResult], requested_crop: str = ""
    ) -> dict[str, ExtractionResult]:
        """
        Extract from several sources in a single LLM call.

        Batching is what keeps a research pass from tripping rate limits --
        one call per batch instead of one call per source. Each source
        still gets an independent extraction (see BATCH_EXTRACTION_SYSTEM_PROMPT's
        no-contamination rule), and its Reference (DOI/URL/authors) is
        attached here in Python from the source object, never from what the
        model returns, so batching can't blur traceability.
        """
        if not sources:
            return {}
        if len(sources) == 1:
            source = sources[0]
            return {self._source_key(source): self.extract_from_source(source, requested_crop=requested_crop)}

        id_to_source: dict[str, SearchResult] = {}
        passages = []
        for i, source in enumerate(sources, start=1):
            source_id = f"S{i}"
            id_to_source[source_id] = source
            passages.append(
                BATCH_PASSAGE_TEMPLATE.format(
                    source_id=source_id,
                    title=source.title or "",
                    authors=", ".join(source.authors) or "Unknown",
                    published_year=source.published_year or "Unknown",
                    url=source.url or "",
                    doi=source.doi or "",
                    source_type=source.source_type.value,
                    text=source.full_text or source.snippet or "",
                )
            )

        user_prompt = BATCH_EXTRACTION_USER_PROMPT.format(count=len(sources), passages="\n\n".join(passages))

        try:
            raw = self.llm_service.complete_json(BATCH_EXTRACTION_SYSTEM_PROMPT, user_prompt, max_tokens=8000)
        except LLMServiceError as e:
            logger.error("Batch extraction failed for %d sources: %s", len(sources), e)
            return {
                self._source_key(source): ExtractionResult(
                    status=ExtractionStatus.UNKNOWN, message=f"Batch extraction call failed: {e}"
                )
                for source in sources
            }

        raw_results = raw.get("results") if isinstance(raw, dict) else None
        if not isinstance(raw_results, list):
            logger.warning("Batch extractor returned malformed 'results' for %d sources.", len(sources))
            raw_results = []

        results: dict[str, ExtractionResult] = {}
        seen_ids: set[str] = set()
        for entry in raw_results:
            if not isinstance(entry, dict):
                continue
            source_id = str(entry.get("source_id") or "").strip()
            source = id_to_source.get(source_id)
            if source is None:
                # No source to attribute this evidence to -- discard rather
                # than guess which passage it belonged to.
                logger.warning("Batch extractor returned an unknown source_id '%s'; discarding.", source_id)
                continue
            seen_ids.add(source_id)
            result = self._build_extraction_result(entry, source, requested_crop)
            log_metadata(
                source_title=source.title[:120],
                source_type=source.source_type.value,
                crop_extracted=result.crop,
                wastes_extracted=len(result.wastes),
                status=result.status.value,
            )
            results[self._source_key(source)] = result

        for source_id, source in id_to_source.items():
            if source_id in seen_ids:
                continue
            logger.warning(
                "Source '%s' (source_id=%s) was missing from batch results; recording as UNKNOWN.",
                source.title, source_id,
            )
            results[self._source_key(source)] = ExtractionResult(
                status=ExtractionStatus.UNKNOWN, message="Source omitted from batch extraction results."
            )

        return results

    @staticmethod
    def _source_key(source: SearchResult) -> str:
        return source.doi or source.url or source.title

    def _build_extraction_result(
        self, raw: dict, source: SearchResult, requested_crop: str
    ) -> ExtractionResult:
        crop_name = str(raw.get("crop") or "").strip()
        status_str = str(raw.get("status") or "UNKNOWN").upper()
        status = ExtractionStatus.SUCCESS if status_str == "SUCCESS" and crop_name else ExtractionStatus.UNKNOWN

        if not crop_name:
            return ExtractionResult(status=ExtractionStatus.UNKNOWN, message="No crop identified in source.")

        wastes: list[Waste] = []
        for raw_waste in raw.get("wastes", []) or []:
            try:
                waste = self._build_waste(raw_waste, source)
                if waste is not None:
                    wastes.append(waste)
            except Exception as e:  # noqa: BLE001
                logger.warning("Skipping malformed waste entry from source '%s': %s", source.title, e)

        return ExtractionResult(
            crop=crop_name,
            scientific_name=str(raw.get("scientific_name") or ""),
            aliases=[str(a) for a in raw.get("aliases", []) if str(a).strip()],
            status=status,
            evidence_source=EvidenceSource.DOCUMENT,
            wastes=wastes,
        )

    def _build_waste(self, raw_waste: dict, source: SearchResult) -> Optional[Waste]:
        name = str(raw_waste.get("name") or "").strip()
        if not name:
            return None

        confidence = _safe_float(raw_waste.get("confidence"), default=0.80)
        reference = source.to_reference(snippet_override=str(raw_waste.get("description") or "")[:500])

        composition = [
            Composition(
                component=str(c.get("component", "")),
                value=str(c.get("value", "")),
                unit=c.get("unit") or None,
                confidence=_safe_float(c.get("confidence"), default=confidence),
                evidence_source=EvidenceSource.DOCUMENT,
                references=[reference],
            )
            for c in raw_waste.get("composition", []) or []
            if c.get("component") and str(c.get("value") or "").strip()
        ]

        transformations = [
            Transformation(
                input_waste=str(t.get("input_waste") or name),
                process=str(t.get("process", "")),
                output_product=str(t.get("output_product", "")),
                description=str(t.get("description", "")),
                confidence=_safe_float(t.get("confidence"), default=confidence),
                evidence_source=EvidenceSource.DOCUMENT,
                references=[reference],
            )
            for t in raw_waste.get("transformations", []) or []
            if t.get("process") or t.get("output_product")
        ]

        def build_applications(key: str, category: str) -> list[Application]:
            return [
                Application(
                    name=str(a.get("name", "")),
                    category=category,
                    description=str(a.get("description", "")),
                    confidence=_safe_float(a.get("confidence"), default=confidence),
                    evidence_source=EvidenceSource.DOCUMENT,
                    references=[reference],
                )
                for a in raw_waste.get(key, []) or []
                if a.get("name")
            ]

        strength_str = str(raw_waste.get("evidence_strength", "MEDIUM")).upper()
        try:
            strength = EvidenceStrength(strength_str)
        except ValueError:
            strength = EvidenceStrength.MEDIUM

        return Waste(
            name=name,
            canonical_name=str(raw_waste.get("canonical_name") or name).strip(),
            category=str(raw_waste.get("category", "")),
            plant_part=str(raw_waste.get("plant_part", "")),
            description=str(raw_waste.get("description", "")),
            harvest_stage=raw_waste.get("harvest_stage") or None,
            composition=composition,
            # physical_properties/chemical_properties (dict[str, str]) and
            # final_products/advantages/limitations (list[str]) are coerced
            # by Waste's own field_validators -- the model sometimes wraps
            # an item in an object where a plain string was asked for, and
            # the fix belongs at the Pydantic boundary every Waste passes
            # through, not duplicated here per field. See models.Waste's
            # coerce_string_lists / coerce_property_maps.
            physical_properties=raw_waste.get("physical_properties"),
            chemical_properties=raw_waste.get("chemical_properties"),
            transformations=transformations,
            final_products=raw_waste.get("final_products") or [],
            industrial_applications=build_applications("industrial_applications", "INDUSTRIAL"),
            agricultural_applications=build_applications("agricultural_applications", "AGRICULTURAL"),
            environmental_applications=build_applications("environmental_applications", "ENVIRONMENTAL"),
            advantages=raw_waste.get("advantages") or [],
            limitations=raw_waste.get("limitations") or [],
            confidence=confidence,
            evidence_source=EvidenceSource.DOCUMENT,
            evidence_strength=strength,
            references=[reference],
        )


def _safe_float(value, default: float = 0.0) -> float:
    try:
        return float(value)
    except (TypeError, ValueError):
        return default
