"""Waste knowledge endpoints consumed by the AgriGuide frontend."""
from __future__ import annotations

from fastapi import APIRouter, Query

from api.schemas import (
    ForCropsRequest,
    ForCropsResponse,
    MarketplaceSuggestionsResponse,
)
from api import service as waste_service

router = APIRouter(prefix="/waste", tags=["waste"])


@router.post("/for-crops", response_model=ForCropsResponse)
def for_crops(body: ForCropsRequest) -> ForCropsResponse:
    """
    Batch lookup: given the 5 recommended agri culture keys, return waste
    valorization profiles from the local knowledge base.
    """
    profiles = waste_service.profiles_for_cultures(body.cultures)
    return ForCropsResponse(profiles=profiles)


@router.get("/marketplace-suggestions", response_model=MarketplaceSuggestionsResponse)
def marketplace_suggestions(
    culture: str = Query(..., description="Agri culture key, e.g. mais"),
    limit: int = Query(4, ge=1, le=8),
) -> MarketplaceSuggestionsResponse:
    """Wastes the farmer can list on the marketplace after harvesting this crop."""
    return waste_service.marketplace_suggestions(culture, limit=limit)


@router.post("/reload")
def reload_knowledge() -> dict:
    """Dev helper: clear the in-memory KB cache after editing the JSON file."""
    kb = waste_service.reload_kb()
    return {"status": "ok", "num_crops": len(kb.crops)}
