"""
Core domain models for the Agricultural Waste Intelligence Agent.

These models are the single source of truth for the shape of data flowing
between the researcher, extractor, validator, knowledge base, and reasoner
agents. Every LLM JSON output is parsed and validated against these models
before being trusted anywhere else in the system.
"""
from __future__ import annotations

import uuid
from datetime import datetime, timezone
from enum import Enum
from typing import Optional

from pydantic import BaseModel, Field, field_validator


# ======================================================================
# Enums
# ======================================================================

class EvidenceSource(str, Enum):
    DOCUMENT = "DOCUMENT"          # scientific paper / web page text
    LLM = "LLM"                    # internal model knowledge
    NONE = "NONE"                  # no evidence at all (UNKNOWN case)


class EvidenceStrength(str, Enum):
    HIGH = "HIGH"
    MEDIUM = "MEDIUM"
    LOW = "LOW"


class ExtractionStatus(str, Enum):
    SUCCESS = "SUCCESS"
    MODEL_KNOWLEDGE = "MODEL_KNOWLEDGE"
    UNKNOWN = "UNKNOWN"


class SourceType(str, Enum):
    ACADEMIC_PAPER = "ACADEMIC_PAPER"      # Semantic Scholar / CrossRef
    WEB_PAGE = "WEB_PAGE"                  # Tavily / Serper result
    UPLOADED_PDF = "UPLOADED_PDF"          # secondary path
    LLM_INTERNAL = "LLM_INTERNAL"


# ======================================================================
# Evidence / Reference
# ======================================================================

class Reference(BaseModel):
    """A single traceable piece of evidence backing a fact."""

    source_type: SourceType
    title: str = ""
    url: Optional[str] = None
    doi: Optional[str] = None
    authors: list[str] = Field(default_factory=list)
    published_year: Optional[int] = None
    page: Optional[int] = None
    snippet: str = Field(default="", description="The exact excerpt that supports the extracted fact")
    retrieved_at: str = Field(default_factory=lambda: datetime.now(timezone.utc).isoformat())

    def short_citation(self) -> str:
        """Human-readable citation string, e.g. for display in the UI."""
        if self.authors:
            author_part = self.authors[0] + (" et al." if len(self.authors) > 1 else "")
        else:
            author_part = self.title[:40] if self.title else "Unknown source"
        year_part = f" ({self.published_year})" if self.published_year else ""
        return f"{author_part}{year_part}"


# ======================================================================
# Waste sub-entities
# ======================================================================

class Transformation(BaseModel):
    """One step in a valorization chain, e.g. Rice Husk -> Biochar -> Water Filtration."""

    input_waste: str
    process: str = Field(description="e.g. 'Pyrolysis', 'Composting', 'Fermentation'")
    output_product: str
    description: str = ""
    confidence: float = 0.0
    evidence_source: EvidenceSource = EvidenceSource.NONE
    references: list[Reference] = Field(default_factory=list)


class Composition(BaseModel):
    """Chemical/physical composition entry, e.g. 'Cellulose: 35-40%'."""

    component: str
    value: str = Field(description="Reported value/range as stated in source, kept as text (e.g. '35-40%')")
    unit: Optional[str] = None
    confidence: float = 0.0
    evidence_source: EvidenceSource = EvidenceSource.NONE
    references: list[Reference] = Field(default_factory=list)


class Application(BaseModel):
    """A downstream application/use of a final product."""

    name: str
    category: str = Field(description="'INDUSTRIAL' | 'AGRICULTURAL' | 'ENVIRONMENTAL' | 'OTHER'")
    description: str = ""
    environmental_benefit: Optional[str] = None
    confidence: float = 0.0
    evidence_source: EvidenceSource = EvidenceSource.NONE
    references: list[Reference] = Field(default_factory=list)


# ======================================================================
# Waste
# ======================================================================

class Waste(BaseModel):
    """A single agricultural waste/byproduct entity belonging to a crop."""

    id: str = Field(default_factory=lambda: str(uuid.uuid4()))
    name: str
    canonical_name: str = ""
    category: str = Field(default="", description="e.g. 'Leaves', 'Husk', 'Bagasse', 'Peel', 'Stalk'")
    plant_part: str = ""
    description: str = ""
    harvest_stage: Optional[str] = None

    composition: list[Composition] = Field(default_factory=list)
    physical_properties: dict[str, str] = Field(default_factory=dict)
    chemical_properties: dict[str, str] = Field(default_factory=dict)

    transformations: list[Transformation] = Field(default_factory=list)
    final_products: list[str] = Field(default_factory=list)
    industrial_applications: list[Application] = Field(default_factory=list)
    agricultural_applications: list[Application] = Field(default_factory=list)
    environmental_applications: list[Application] = Field(default_factory=list)

    advantages: list[str] = Field(default_factory=list)
    limitations: list[str] = Field(default_factory=list)

    confidence: float = 0.0
    evidence_source: EvidenceSource = EvidenceSource.NONE
    evidence_strength: EvidenceStrength = EvidenceStrength.LOW
    references: list[Reference] = Field(default_factory=list)

    created_at: str = Field(default_factory=lambda: datetime.now(timezone.utc).isoformat())
    updated_at: str = Field(default_factory=lambda: datetime.now(timezone.utc).isoformat())

    @field_validator("final_products", "advantages", "limitations", mode="before")
    @classmethod
    def coerce_string_lists(cls, value):
        """
        Accept dict-shaped items in fields declared as list[str].

        The extraction schema asks for plain strings, but the model
        regularly wraps items in an object instead
        ({"name": ..., "description": ..., "confidence": ...}). Handled
        here rather than in the extractor because this is the boundary
        every waste passes through: fixing it per-field in the extractor
        meant the same bug resurfaced in each new field
        (chemical_properties, then advantages, then final_products).
        A field added later inherits the coercion just by being listed here.

        "name" is checked before "description" because these fields hold
        short labels; the longer prose only serves as a fallback.
        """
        if not isinstance(value, list):
            return value

        out: list[str] = []
        for item in value:
            if isinstance(item, dict):
                text = item.get("name") or item.get("description") or item.get("value") or ""
            else:
                text = item
            text = str(text).strip()
            if text:
                out.append(text)
        return out

    @field_validator("physical_properties", "chemical_properties", mode="before")
    @classmethod
    def coerce_property_maps(cls, value):
        """
        Accept nested objects as values in dict[str, str] property maps.

        Same root cause as `coerce_string_lists`: the model may return
        {"biodegradability": {"value": "biodegradable", "confidence": 0.95}}
        where a plain string was asked for.
        """
        if not isinstance(value, dict):
            return {} if value is None else value

        out: dict[str, str] = {}
        for key, item in value.items():
            if isinstance(item, dict):
                text = item.get("value") or item.get("description") or item.get("name") or str(item)
            elif isinstance(item, (list, tuple)):
                text = ", ".join(str(v) for v in item)
            elif item is None:
                continue
            else:
                text = item
            out[str(key)] = str(text).strip()
        return out

    @field_validator("confidence")
    @classmethod
    def clamp_confidence(cls, v: float) -> float:
        return max(0.0, min(1.0, v))

    def merge_with(self, other: "Waste") -> "Waste":
        """
        Merge another Waste entry (same canonical entity, new evidence) into this one.
        Keeps the higher-confidence scalar fields and unions list fields, deduplicating
        references by (url or doi or title).
        """
        merged = self.model_copy(deep=True)

        if other.confidence > merged.confidence:
            merged.description = other.description or merged.description
            merged.confidence = other.confidence
            merged.evidence_source = other.evidence_source
            merged.evidence_strength = other.evidence_strength

        merged.composition = _dedupe_models(merged.composition + other.composition, key=lambda c: c.component.lower())
        merged.transformations = _dedupe_models(
            merged.transformations + other.transformations,
            key=lambda t: (t.input_waste.lower(), t.process.lower(), t.output_product.lower()),
        )
        merged.final_products = sorted(set(merged.final_products + other.final_products))
        merged.industrial_applications = _dedupe_models(
            merged.industrial_applications + other.industrial_applications, key=lambda a: a.name.lower()
        )
        merged.agricultural_applications = _dedupe_models(
            merged.agricultural_applications + other.agricultural_applications, key=lambda a: a.name.lower()
        )
        merged.environmental_applications = _dedupe_models(
            merged.environmental_applications + other.environmental_applications, key=lambda a: a.name.lower()
        )
        merged.advantages = sorted(set(merged.advantages + other.advantages))
        merged.limitations = sorted(set(merged.limitations + other.limitations))
        merged.references = _dedupe_references(merged.references + other.references)
        merged.updated_at = datetime.now(timezone.utc).isoformat()
        return merged


def _dedupe_models(items: list, key) -> list:
    seen: set = set()
    out = []
    for item in items:
        k = key(item)
        if k not in seen:
            seen.add(k)
            out.append(item)
    return out


def _dedupe_references(refs: list[Reference]) -> list[Reference]:
    seen: set = set()
    out = []
    for r in refs:
        k = r.doi or r.url or r.title
        if k and k not in seen:
            seen.add(k)
            out.append(r)
    return out


# ======================================================================
# Crop
# ======================================================================

class Crop(BaseModel):
    """A crop entity, root of the canonical knowledge tree."""

    id: str = Field(default_factory=lambda: str(uuid.uuid4()))
    name: str
    canonical_name: str = ""
    scientific_name: str = ""
    aliases: list[str] = Field(default_factory=list)
    wastes: list[Waste] = Field(default_factory=list)

    created_at: str = Field(default_factory=lambda: datetime.now(timezone.utc).isoformat())
    updated_at: str = Field(default_factory=lambda: datetime.now(timezone.utc).isoformat())
    last_research_at: Optional[str] = None

    def find_waste(self, name: str) -> Optional[Waste]:
        norm = name.strip().lower()
        for w in self.wastes:
            if w.canonical_name.lower() == norm or w.name.lower() == norm:
                return w
        return None

    def upsert_waste(self, waste: Waste) -> None:
        existing = self.find_waste(waste.canonical_name or waste.name)
        if existing:
            merged = existing.merge_with(waste)
            self.wastes = [merged if w.id == existing.id else w for w in self.wastes]
        else:
            self.wastes.append(waste)
        self.updated_at = datetime.now(timezone.utc).isoformat()


class KnowledgeBase(BaseModel):
    """Top-level container persisted to canonical_knowledge.json."""

    version: str = "1.0.0"
    crops: list[Crop] = Field(default_factory=list)
    updated_at: str = Field(default_factory=lambda: datetime.now(timezone.utc).isoformat())

    def find_crop(self, name: str) -> Optional[Crop]:
        norm = name.strip().lower()
        for c in self.crops:
            if c.canonical_name.lower() == norm or c.name.lower() == norm or norm in [a.lower() for a in c.aliases]:
                return c
        import re
        from agents.validator import KNOWN_CROP_NAMES

        matches = [base for base in KNOWN_CROP_NAMES if re.search(r"\b" + re.escape(base) + r"\b", norm)]
        if len(matches) == 1:
            base = matches[0]
            for c in self.crops:
                if c.canonical_name.lower() == base or c.name.lower() == base:
                    return c

        return None

    def upsert_crop(self, crop: Crop) -> Crop:
        existing = self.find_crop(crop.canonical_name or crop.name)
        if existing:
            existing.aliases = sorted(set(existing.aliases + crop.aliases))
            existing.scientific_name = existing.scientific_name or crop.scientific_name
            for w in crop.wastes:
                existing.upsert_waste(w)
            existing.updated_at = datetime.now(timezone.utc).isoformat()
            self.updated_at = existing.updated_at
            return existing
        self.crops.append(crop)
        self.updated_at = datetime.now(timezone.utc).isoformat()
        return crop

    def stats(self) -> dict:
        n_wastes = sum(len(c.wastes) for c in self.crops)
        n_transformations = sum(len(w.transformations) for c in self.crops for w in c.wastes)
        n_products = len(
            {p for c in self.crops for w in c.wastes for p in w.final_products}
        )
        return {
            "num_crops": len(self.crops),
            "num_wastes": n_wastes,
            "num_transformations": n_transformations,
            "num_products": n_products,
        }


# ======================================================================
# Search / Extraction intermediate models
# ======================================================================

class SearchResult(BaseModel):
    """A single result returned by any search provider (web or academic)."""

    source_type: SourceType
    title: str = ""
    url: Optional[str] = None
    doi: Optional[str] = None
    authors: list[str] = Field(default_factory=list)
    published_year: Optional[int] = None
    snippet: str = ""
    full_text: Optional[str] = Field(default=None, description="Populated if the full text/abstract was fetched")

    def to_reference(self, page: Optional[int] = None, snippet_override: Optional[str] = None) -> Reference:
        return Reference(
            source_type=self.source_type,
            title=self.title,
            url=self.url,
            doi=self.doi,
            authors=self.authors,
            published_year=self.published_year,
            page=page,
            snippet=snippet_override or self.snippet,
        )


class ExtractionResult(BaseModel):
    """Raw output of the extractor agent for a single source, before validation."""

    crop: str = ""
    scientific_name: str = ""
    aliases: list[str] = Field(default_factory=list)
    status: ExtractionStatus = ExtractionStatus.UNKNOWN
    evidence_source: EvidenceSource = EvidenceSource.NONE
    wastes: list[Waste] = Field(default_factory=list)
    message: str = ""


class QAAnswer(BaseModel):
    """Final structured answer returned by the reasoner agent to the UI."""

    answer: str
    status: ExtractionStatus
    crop_names: list[str] = Field(default_factory=list)
    references: list[Reference] = Field(default_factory=list)
    triggered_live_research: bool = False
