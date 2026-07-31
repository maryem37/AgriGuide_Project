"""
Pydantic models shared across the pipeline. Kept in one file so every
service and the router agree on the same shapes.

Ported from the standalone `agri-advisor-parcelle` prototype, plus a
new request/response pair (`AnalyzeRequest` / `AnalyzeResponse`) that
wires the pipeline to this project's actual DB schema
(`database/schema.sql` — `terrains` / `land_profiles` /
`crop_recommendations`) and to `frontend/src/lib/businessApi.ts`'s
`CropRecommendation` shape, so the agent Business can eventually
consume this agent's real output instead of its mocks.
"""
from pydantic import BaseModel, Field
from typing import Optional, Literal


class Coordinate(BaseModel):
    lat: float
    lon: float


class ParcelRequest(BaseModel):
    point: Coordinate
    manual_geojson: Optional[dict] = None  # user-drawn fallback boundary


class ParcelResolution(BaseModel):
    resolved: bool
    source: Literal["cadastre", "rpg", "manual", "unresolved"]
    geometry: Optional[dict] = None
    centroid: Optional[Coordinate] = None
    parcel_id: Optional[str] = None
    rpg_id_parcel: Optional[str] = None  # RPG's own id_parcel field — distinct ID system from cadastre's idu; needed to correctly exclude this parcel from its own RPG-neighbor lookup
    area_ha: Optional[float] = None
    area_m2: Optional[float] = None
    crop_declared: Optional[str] = None
    is_agricultural: Optional[bool] = None  # RPG registration check
    agricultural_note: Optional[str] = None  # explains the check's limits
    warning: Optional[str] = None


class NeighborParcel(BaseModel):
    geometry: dict
    crop_code: Optional[str] = None


class NeighborCropContext(BaseModel):
    neighbor_count: int
    crop_distribution_pct: dict[str, float]  # e.g. {"Blé tendre": 45.0, "Maïs": 30.0, ...} — keys are display names via taxonomy.get_display_name
    neighbors: list[NeighborParcel]
    note: str


class SoilData(BaseModel):
    source: Literal["soilgrids", "inrae", "unavailable"]
    ph: Optional[float] = None
    nitrogen_g_kg: Optional[float] = None
    organic_carbon_g_kg: Optional[float] = None
    sand_pct: Optional[float] = None
    clay_pct: Optional[float] = None
    silt_pct: Optional[float] = None
    cec_cmolkg: Optional[float] = None          # Cation Exchange Capacity — proxy for K/P retention
    bulk_density_kg_dm3: Optional[float] = None  # Bulk density (soil compaction)
    coarse_fragments_pct: Optional[float] = None # Stones/gravel volume fraction
    depth_cm: Optional[str] = None
    warning: Optional[str] = None


class WeatherData(BaseModel):
    source: Literal["open-meteo", "unavailable"]
    daily_temp_mean_c: Optional[list[Optional[float]]] = None
    daily_precip_mm: Optional[list[Optional[float]]] = None
    daily_et0_mm: Optional[list[Optional[float]]] = None  # reference evapotranspiration, for irrigation estimate
    daily_dates: Optional[list[str]] = None
    warning: Optional[str] = None


class RetrievedChunk(BaseModel):
    chunk_id: str
    text: str
    source_document: str
    crop: Optional[str] = None
    region: Optional[str] = None
    topic: Optional[str] = None
    score: float


class CropRecommendation(BaseModel):
    """Raw output of `ml_service.recommend_crops` — internal pipeline shape."""
    crop: str
    suitability_score: float
    reasoning_features: dict


class AgroCalcEstimate(BaseModel):
    """
    Fertilizer (nitrogen) and irrigation estimates for a given crop —
    computed with published reference formulas/constants (COMIFER-style
    nitrogen balance, FAO-56 crop water balance), NOT by the LLM.
    Explicitly a simplified placeholder: nitrogen supply is estimated from
    soil organic carbon, not a real Nmin soil test; irrigation is based on
    the 16-day forecast window, not a full growing season. Both facts are
    carried in the notes fields so the report states the limitation
    honestly rather than presenting placeholder precision as authoritative.
    """
    crop: str
    # Nitrogen
    n_dose_kg_ha: Optional[float] = None
    n_besoins_kg_ha: Optional[float] = None       # crop need, from yield objective
    n_fournitures_kg_ha: Optional[float] = None   # estimated soil supply
    yield_objective_q_ha: Optional[float] = None
    n_method_note: Optional[str] = None
    # Irrigation
    irrigation_need_mm: Optional[float] = None
    irrigation_window_days: Optional[int] = None
    total_et0_mm: Optional[float] = None
    total_effective_precip_mm: Optional[float] = None
    irrigation_method_note: Optional[str] = None
    warning: Optional[str] = None


class SynthesisJSON(BaseModel):
    """Stage 1 output — every claim traceable to a source chunk."""
    parcel_id: Optional[str]
    location: Coordinate
    soil_summary: dict
    weather_summary: dict
    weather_stats: dict = Field(default_factory=dict)  # precomputed in Python (mean/min/max temp, total precip, rainy-day count) — ground truth for the audit, independent of whatever Stage 1 computed into weather_summary
    vegetation_summary: dict
    dl_observation_summary: dict = Field(default_factory=dict)  # set directly from DLCropObservation.model_dump() in Python — Stage 1 never sees or touches this, avoiding the LLM-recomputation risk found with weather_summary
    dl_mismatch_note: Optional[str] = None  # pre-formatted French sentence, computed in Python — Stage 2 copies it verbatim rather than generating it
    agro_calc_summary: dict = Field(default_factory=dict)  # set directly from AgroCalcEstimate.model_dump() in Python — same treatment, never LLM-generated
    crop_recommendations: list[CropRecommendation]
    grounded_claims: list[dict]  # {"claim": str, "source_chunk_id": str}
    data_gaps: list[str]


class AdvisorReport(BaseModel):
    parcel_id: Optional[str]
    report_markdown: str
    warnings: list[str] = Field(default_factory=list)
    unverified_figures: list[str] = Field(default_factory=list)  # numbers in the report not traceable to source data


class VegetationData(BaseModel):
    source: Literal["sentinel-2", "unavailable"]
    mean_ndvi: Optional[float] = None  # -1 to 1; roughly: <0.2 bare/sparse, 0.2-0.5 moderate, >0.5 dense healthy vegetation
    observation_window_days: Optional[int] = None
    valid_pixel_count: Optional[int] = None  # cloud-free samples used in the mean — low count = less reliable
    warning: Optional[str] = None


class DLCropObservation(BaseModel):
    """Phase B — descriptive only, same treatment as VegetationData/NDVI.
    NOT fed into ml_service.py's crop-suitability scoring."""
    source: Literal["dl-tempcnn-breizhcrops", "unavailable"]
    predicted_class_fr: Optional[str] = None
    predicted_class_en: Optional[str] = None
    confidence: Optional[float] = None  # softmax probability of the predicted class, 0-1
    observation_timesteps: Optional[int] = None  # real cloud-free acquisitions used — low count = less reliable
    warning: Optional[str] = None


# ---------------------------------------------------------------------------
# New — /agriculture/analyze request/response.
#
# CropRecommendationOut mirrors `crop_recommendations` in `database/schema.sql`
# field-for-field (rang, culture, score_compatibilite, besoins_*,
# feature_importance) AND `frontend/src/lib/businessApi.ts`'s
# `CropRecommendation` type, so the agent Business can eventually call this
# agent directly instead of using mock data (see its README §"Prochaines
# étapes").
# ---------------------------------------------------------------------------


class AnalyzeRequest(BaseModel):
    point: Coordinate
    manual_geojson: Optional[dict] = None
    terrain_id: Optional[str] = None  # if provided, results are persisted against this terrain (must already exist in `terrains`)
    yield_objective_q_ha: Optional[float] = None  # optional override for the fertilizer calculation


class CropRecommendationOut(BaseModel):
    rang: int
    culture: str
    score_compatibilite: float  # 0-100
    cycle_jours: int
    besoins_irrigation: dict
    besoins_engrais: dict
    besoins_pesticides: dict
    feature_importance: dict


class AnalyzeResponse(BaseModel):
    terrain_id: Optional[str] = None
    land_profile_id: Optional[str] = None
    persisted: bool = False
    parcel: ParcelResolution
    soil: SoilData
    weather: WeatherData
    weather_stats: dict = Field(default_factory=dict)
    vegetation: VegetationData
    dl_observation: DLCropObservation
    neighbors: Optional[NeighborCropContext] = None
    crop_recommendations: list[CropRecommendationOut]
    agro_calc_top_crop: AgroCalcEstimate
    report: Optional[AdvisorReport] = None  # None when MISTRAL_API_KEY / RAG corpus aren't configured — degrades gracefully rather than failing the whole analysis
    warnings: list[str] = Field(default_factory=list)
