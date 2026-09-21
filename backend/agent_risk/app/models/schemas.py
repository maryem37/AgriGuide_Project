"""Pydantic data schemas for agent_risk microservice."""

from __future__ import annotations
from datetime import datetime, timezone
from typing import Optional
from pydantic import BaseModel, Field


# ---------------------------------------------------------------------------
# Input Schemas from Agriculture Agent
# ---------------------------------------------------------------------------

class CropRecommendationInput(BaseModel):
    rang: int
    culture: str
    score_compatibilite: float = Field(ge=0, le=100)
    cycle_jours: int = Field(gt=0)
    besoins_irrigation: dict = Field(default_factory=dict)
    besoins_engrais: dict = Field(default_factory=dict)
    besoins_pesticides: dict = Field(default_factory=dict)
    feature_importance: dict = Field(default_factory=dict)


# ---------------------------------------------------------------------------
# Climate Risk Schemas (Belhsen et al., 2026, JRACR)
# ---------------------------------------------------------------------------

class ClimateRiskRequest(BaseModel):
    """Input for POST /risk/climate"""
    lat: float = Field(ge=-90, le=90)
    lon: float = Field(ge=-180, le=180)
    crop_type: str = Field(default="ble_tendre")
    parcel_id: Optional[str] = "PARCEL-DEFAULT"
    ndvi_current: Optional[float] = Field(default=None, ge=-1.0, le=1.0)
    ndvi_max_baseline: Optional[float] = Field(default=0.85, ge=0.0, le=1.0)


class RiskBreakdown(BaseModel):
    spi_3m: float = Field(description="Standardized 3-month rainfall index (SPI / Gamma distribution)")
    spei_3m: float = Field(description="Standardized 3-month water balance index (SPEI / Pearson III distribution)")
    ndvi_decay: float = Field(description="Relative Sentinel-2 canopy vegetation decay (0.0 if missing)")
    composite_index: float = Field(description="Composite index: 0.45*SPI + 0.40*SPEI - 0.15*NDVI_decay")
    drought_component_score: float = Field(ge=0, le=100, description="Drought component score (100 * Φ(-SPEI))")
    vegetation_stress_score: float = Field(ge=0, le=100, description="Vegetation stress score (100 * NDVI_decay)")
    formula_explanation: str = Field(
        default="risk_score = 100 * Φ(-composite_index). Drought score isolates SPEI; vegetation stress score isolates NDVI decay.",
        description="Explanation of risk_score synthesis"
    )


class InsuranceRecommendation(BaseModel):
    suggested_coverage: str
    estimated_annual_premium_eur_ha: float
    payout_trigger_threshold: float
    payout_exhaustion_threshold: float
    reasoning: str


class ClimateRiskResponse(BaseModel):
    parcel_id: str
    crop_type: str
    risk_score: int = Field(ge=0, le=100)
    risk_level: str  # 'FAIBLE' | 'MODÉRÉ' | 'ÉLEVÉ' | 'CRITIQUE'
    risk_breakdown: RiskBreakdown
    insurance_recommendation: InsuranceRecommendation
    methodology_note: str = (
        "Note V1 (Evidence-Based) : Basé sur le framework de Belhsen et al. (2026, JRACR, doi:10.54560/jracr.v16i2.726). "
        "Pondération heuristique V1 (0.45 SPI + 0.40 SPEI - 0.15 NDVI decay, non calibrée statistiquement), "
        "à ajuster via régression Lasso sur données Agreste en V2. Les seuils de déclenchement (s_trigger) et d'épuisement (s_exhaustion) "
        "sont des paramètres fixes heuristiques (calibration RBR à venir en V2). Les estimations de prime sont données à titre "
        "purement indicatif d'aide à la décision et ne constituent pas un devis actuariel ferme."
    )


# ---------------------------------------------------------------------------
# Crop Mix Optimization Schemas (linprog + HHI)
# ---------------------------------------------------------------------------

class CropMixRequest(BaseModel):
    """Input for POST /risk/crop-mix"""
    terrain_id: str
    superficie_disponible_ha: float = Field(gt=0, description="Total farm area available (ha)")
    budget_input: float = Field(gt=0, description="Total available farm budget (€)")
    crop_recommendations: list[CropRecommendationInput] = Field(min_length=1, description="Agriculture Agent crop recommendations")
    max_single_crop_share: float = Field(default=0.50, ge=0.10, le=1.0, description="Maximum single crop acreage cap (e.g., 0.50 = 50% max)")
    min_compatibility_score: float = Field(default=40.0, ge=0.0, le=100.0, description="Minimum agronomic compatibility threshold")


class CropAllocation(BaseModel):
    culture: str
    hectares_alloues: float = Field(ge=0, description="Allocated acreage (ha)")
    pourcentage_surface: float = Field(ge=0, le=100, description="Acreage share (%)")
    profit_estime_eur: float
    cout_total_eur: float
    score_compatibilite: float


class CropMixResponse(BaseModel):
    terrain_id: str
    superficie_totale_ha: float
    superficie_utilisee_ha: float
    budget_total_eur: float
    budget_utilise_eur: float
    profit_total_estime_eur: float
    roi_global_pct: float
    diversification_hhi_score: float = Field(description="Herfindahl-Hirschman Index (0-10000): < 1500 diversified, > 2500 concentrated")
    diversification_label: str  # 'DIVERSIFIÉ' | 'MODÉRÉ' | 'CONCENTRÉ'
    optimization_status: str  # 'OPTIMAL' | 'SUB_OPTIMAL' | 'INFEASIBLE'
    allocations: list[CropAllocation]
    methodology_note: str = (
        "Note V1 (Business Heuristic Score) : Optimisation d'asassolement par programmation linéaire (scipy.optimize.linprog / HiGHS) "
        "maximisant le profit net global sous contraintes de surface totale, budget disponible "
        "et plafonnement anti-monoculture (max 50% de la surface par culture). "
        "L'indice Herfindahl-Hirschman (HHI) est un proxy d'orientation produit d'ingénierie interne (sans lien avec la modélisation publiée de Belhsen et al. 2026). "
        "Les contraintes de rotation pluriannuelle et les variances financières sont prévues pour la V2."
    )
