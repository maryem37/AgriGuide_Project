"""Pydantic schemas for the AgriGuide waste HTTP API."""
from __future__ import annotations

from pydantic import BaseModel, Field


class ForCropsRequest(BaseModel):
    cultures: list[str] = Field(..., min_length=1, max_length=10, description="Agri culture keys, e.g. ble_tendre")


class TransformationOut(BaseModel):
    process: str
    process_label: str
    output_product: str
    output_label: str
    description: str = ""


class ApplicationOut(BaseModel):
    name: str
    name_label: str
    category: str
    description: str = ""
    environmental_benefit: str | None = None


class WasteOut(BaseModel):
    id: str
    name: str
    name_label: str
    category: str = ""
    plant_part: str = ""
    description: str = ""
    composition_summary: list[str] = Field(default_factory=list)
    transformations: list[TransformationOut] = Field(default_factory=list)
    final_products: list[str] = Field(default_factory=list)
    final_products_labels: list[str] = Field(default_factory=list)
    applications: list[ApplicationOut] = Field(default_factory=list)
    advantages: list[str] = Field(default_factory=list)
    confidence: float = 0.0
    # Ready-to-use marketplace copy (French)
    marketplace_title: str = ""
    marketplace_utility: str = ""
    marketplace_description: str = ""


class CropWasteProfile(BaseModel):
    culture: str
    kb_crop_name: str | None = None
    crop_label_fr: str
    found: bool
    scientific_name: str = ""
    wastes: list[WasteOut] = Field(default_factory=list)
    message: str = ""


class ForCropsResponse(BaseModel):
    profiles: list[CropWasteProfile]


class MarketplaceSuggestionsResponse(BaseModel):
    culture: str
    crop_label_fr: str
    found: bool
    harvest_hint: str
    suggestions: list[WasteOut] = Field(default_factory=list)
    message: str = ""
