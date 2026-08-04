"""
Orchestrator router — the "agent" from the project's architecture doc.
Currently a fixed parallel-then-sequential flow rather than a true
tool-calling agent loop (documented MVP simplification, same as the
standalone prototype this was ported from): same data contracts, easy
to swap in real agentic tool-selection later without changing any
service module.
"""
import asyncio

import psycopg2
from fastapi import APIRouter, HTTPException

from app.models.schemas import (
    ParcelRequest,
    ParcelResolution,
    NeighborCropContext,
    AnalyzeRequest,
    AnalyzeResponse,
    CropRecommendationOut,
    Coordinate,
    SoilData,
    WeatherData,
    VegetationData,
    DLCropObservation,
)
from app.services import (
    parcel_service,
    soil_service,
    weather_service,
    satellite_service,
    ml_service,
    agro_calc_service,
    rag_service,
    synthesis_service,
    dl_service,
    persistence_service,
    relief3d_service,
)

router = APIRouter(prefix="/agriculture", tags=["agriculture"])


@router.post("/relief/grid")
async def get_relief_grid(geometry: dict):
    """Return the terrain mesh data and satellite indices for the 3D viewer."""
    if not geometry or "type" not in geometry or "coordinates" not in geometry:
        raise HTTPException(status_code=400, detail="Géométrie GeoJSON de parcelle manquante ou invalide.")
    try:
        return await relief3d_service.build_relief_grid(geometry)
    except Exception as exc:  # noqa: BLE001 - external data sources may fail independently
        raise HTTPException(status_code=502, detail=f"Relief 3D indisponible : {exc}") from exc


@router.post("/relief/orthophoto")
async def get_relief_orthophoto(geometry: dict):
    """Return an IGN orthophoto data URL for the selected 3D texture."""
    if not geometry or "type" not in geometry or "coordinates" not in geometry:
        raise HTTPException(status_code=400, detail="Géométrie GeoJSON de parcelle manquante ou invalide.")
    try:
        return {"image_base64": await asyncio.to_thread(relief3d_service.build_orthophoto_data_url, geometry)}
    except Exception as exc:  # noqa: BLE001 - IGN availability is exposed to the UI
        raise HTTPException(status_code=502, detail=f"Orthophoto IGN indisponible : {exc}") from exc


@router.post("/parcel/resolve", response_model=ParcelResolution)
async def resolve_parcel_only(req: ParcelRequest):
    return await parcel_service.resolve_parcel(req)


@router.post("/parcel/neighbors", response_model=NeighborCropContext)
async def get_neighbors(req: ParcelRequest, radius_m: float = 15_000):
    parcel = await parcel_service.resolve_parcel(req)
    centroid = parcel.centroid or req.point
    return await parcel_service.get_neighboring_crop_context(
        centroid, radius_m=radius_m, exclude_parcel_id=parcel.rpg_id_parcel
    )


def _besoins_for_crop(crop: str, soil: SoilData, weather: WeatherData, yield_objective_q_ha: float | None):
    """Runs the agro-calc formulas for one candidate crop (not just the
    top-ranked one) so every entry in the top-5 list carries real
    fertilizer/irrigation numbers, not just the winner."""
    estimate = agro_calc_service.estimate_fertilizer_and_irrigation(crop, soil, weather, yield_objective_q_ha)
    besoins_irrigation = {
        "irrigation_need_mm": estimate.irrigation_need_mm,
        "irrigation_window_days": estimate.irrigation_window_days,
        "total_et0_mm": estimate.total_et0_mm,
        "total_effective_precip_mm": estimate.total_effective_precip_mm,
        "note": estimate.irrigation_method_note,
    }
    besoins_engrais = {
        "n_dose_kg_ha": estimate.n_dose_kg_ha,
        "n_besoins_kg_ha": estimate.n_besoins_kg_ha,
        "n_fournitures_kg_ha": estimate.n_fournitures_kg_ha,
        "yield_objective_q_ha": estimate.yield_objective_q_ha,
        "note": estimate.n_method_note,
    }
    if estimate.warning:
        besoins_irrigation["warning"] = estimate.warning
        besoins_engrais["warning"] = estimate.warning
    besoins_pesticides = {
        "warning": (
            "Non calculé — nécessite un module BSV (Bulletin de Santé du Végétal) croisant "
            "les données climatiques régionales avec les risques phytosanitaires connus "
            "(voir backend/agent_agriculture/README.md, section \u00ab À ajouter \u00bb)."
        )
    }
    return estimate, besoins_irrigation, besoins_engrais, besoins_pesticides


@router.post("/analyze", response_model=AnalyzeResponse)
async def analyze(req: AnalyzeRequest):
    warnings: list[str] = []

    # 1. Resolve the parcel geometry to analyze — either the farmer's own
    #    saved terrain (authoritative boundary + area from `terrains`,
    #    enriched with a cadastre/RPG lookup at its centroid), or a fresh
    #    point clicked on the map (resolved live against cadastre/RPG).
    terrain_row = None
    if req.terrain_id:
        try:
            terrain_row = persistence_service.get_terrain(req.terrain_id)
        except psycopg2.OperationalError as e:
            raise HTTPException(
                status_code=503,
                detail=(
                    "Base Postgres inaccessible. En local, lancez `docker compose up -d db` "
                    f"(port 5434) et vérifiez DATABASE_URL. Détail : {e}"
                ),
            ) from e
        if not terrain_row:
            raise HTTPException(status_code=404, detail="Terrain introuvable.")
        centroid = Coordinate(lat=terrain_row["centroid_lat"], lon=terrain_row["centroid_lon"])
        parcel = await parcel_service.resolve_parcel(ParcelRequest(point=centroid))
        # The terrain's own hand-drawn boundary is the authoritative one for
        # this farmer's field — a cadastre lookup at the centroid can land on
        # a neighboring cadastral unit, so it's only used to enrich (crop
        # déclaré, statut agricole), never to override the geometry/area.
        parcel.geometry = terrain_row["geometry"]
        parcel.area_ha = terrain_row["superficie_ha"]
        parcel.centroid = centroid
        parcel.resolved = True
        if parcel.source == "unresolved":
            parcel.source = "manual"
    else:
        parcel = await parcel_service.resolve_parcel(ParcelRequest(point=req.point, manual_geojson=req.manual_geojson))
        if not parcel.resolved:
            raise HTTPException(
                status_code=422,
                detail=parcel.warning or "Impossible de résoudre une parcelle à cet endroit.",
            )

    # 2. Parallel data fetch. Satellite NDVI and the DL classifier both need
    #    the actual polygon (not just centroid), so they only run if we have
    #    geometry — fall back gracefully otherwise, same pattern for both.
    #
    #    return_exceptions=True: soil_service/weather_service already catch
    #    their own httpx errors internally and always return a valid
    #    (possibly "unavailable") object, but satellite_service.get_ndvi()
    #    and dl_service.predict_crop() don't have that same internal guard
    #    against *unexpected* exceptions. Without this, one bad response
    #    from either would take down the entire request — including data
    #    that already succeeded — contradicting this project's own
    #    "degrade gracefully" principle.
    results = await asyncio.gather(
        soil_service.get_soil_data(parcel.centroid),
        weather_service.get_weather_data(parcel.centroid),
        satellite_service.get_ndvi(parcel.geometry) if parcel.geometry else asyncio.sleep(0, result=None),
        dl_service.predict_crop(parcel.geometry) if parcel.geometry else asyncio.sleep(0, result=None),
        parcel_service.get_neighboring_crop_context(parcel.centroid, radius_m=15_000, exclude_parcel_id=parcel.rpg_id_parcel),
        return_exceptions=True,
    )
    soil, weather, vegetation, dl_observation, neighbors = results

    if isinstance(soil, Exception):
        soil = SoilData(source="unavailable", warning=f"Erreur inattendue lors de la récupération des données de sol : {soil}")
    if isinstance(weather, Exception):
        weather = WeatherData(source="unavailable", warning=f"Erreur inattendue lors de la récupération des données météo : {weather}")
    if vegetation is None:
        vegetation = VegetationData(source="unavailable", warning="Aucune géométrie de parcelle disponible pour la donnée satellite.")
    elif isinstance(vegetation, Exception):
        vegetation = VegetationData(source="unavailable", warning=f"Erreur inattendue NDVI : {vegetation}")
    if dl_observation is None:
        dl_observation = DLCropObservation(source="unavailable", warning="Aucune géométrie de parcelle disponible pour la classification satellite.")
    elif isinstance(dl_observation, Exception):
        dl_observation = DLCropObservation(source="unavailable", warning=f"Erreur inattendue classification DL : {dl_observation}")
    if isinstance(neighbors, Exception):
        warnings.append(f"Contexte des parcelles voisines indisponible : {neighbors}")
        neighbors = None

    # 3. Rule-based 5-crop scoring + real fertilizer/irrigation numbers for EVERY crop.
    crop_recs = ml_service.recommend_crops(soil, weather)
    crop_recommendations_out: list[CropRecommendationOut] = []
    top_crop_agro = None
    for rank, rec in enumerate(crop_recs, start=1):
        estimate, besoins_irrigation, besoins_engrais, besoins_pesticides = _besoins_for_crop(
            rec.crop, soil, weather, req.yield_objective_q_ha
        )
        if rank == 1:
            top_crop_agro = estimate
        crop_recommendations_out.append(
            CropRecommendationOut(
                rang=rank,
                culture=rec.crop,
                score_compatibilite=round(rec.suitability_score * 100, 2),
                cycle_jours=ml_service.CYCLE_DAYS.get(rec.crop, 0),
                besoins_irrigation=besoins_irrigation,
                besoins_engrais=besoins_engrais,
                besoins_pesticides=besoins_pesticides,
                feature_importance=rec.reasoning_features,
            )
        )
    top_crop = crop_recs[0].crop if crop_recs else None

    # 4. RAG retrieval + two-stage Mistral synthesis — best-effort. Missing
    #    MISTRAL_API_KEY or an empty corpus must not fail the whole
    #    analysis: the real data above (soil/weather/satellite/crops/agro
    #    calc) is still useful and returned regardless.
    report = None
    try:
        chunks = await asyncio.to_thread(
            rag_service.retrieve,
            query=f"bonnes pratiques agronomiques pour {top_crop}" if top_crop else "bonnes pratiques agronomiques",
            crop_filter=top_crop,
        )
        if not chunks and top_crop:
            chunks = await asyncio.to_thread(
                rag_service.retrieve,
                query=f"bonnes pratiques agronomiques pour {top_crop}",
                crop_filter=None,
            )
        synthesis = await synthesis_service.synthesize_stage1(
            parcel, soil, weather, crop_recs, chunks, vegetation, dl_observation, top_crop_agro
        )
        report = await synthesis_service.generate_report(synthesis, parcel)
    except Exception as e:  # noqa: BLE001 — genuinely want to degrade gracefully here (missing key, empty corpus, network issue, ...)
        warnings.append(f"Rapport IA non généré (RAG/LLM indisponible) : {e}")

    # 5. Persist against the terrain, if the caller gave us one — matches
    #    `database/schema.sql`'s land_profiles/crop_recommendations tables.
    land_profile_id = None
    persisted = False
    if req.terrain_id:
        try:
            rpg_historique = None
            if parcel.crop_declared or parcel.parcel_id:
                rpg_historique = {
                    "crop_declared": parcel.crop_declared,
                    "parcel_id": parcel.parcel_id,
                    "rpg_id_parcel": parcel.rpg_id_parcel,
                    "is_agricultural": parcel.is_agricultural,
                }
            land_profile_id = persistence_service.save_land_profile(
                terrain_id=req.terrain_id,
                sol_data=soil.model_dump(),
                satellite_data={**vegetation.model_dump(), "dl_observation": dl_observation.model_dump()},
                rpg_historique=rpg_historique,
                cultures_voisines=neighbors.crop_distribution_pct if neighbors else None,
                climat_data=weather.model_dump(),
            )
            persistence_service.save_crop_recommendations(land_profile_id, crop_recommendations_out)
            persisted = True
        except Exception as e:  # noqa: BLE001 — a DB hiccup shouldn't discard an otherwise-successful analysis
            warnings.append(f"Résultats non persistés en base (erreur DB) : {e}")

    weather_stats = synthesis_service.compute_weather_stats(weather)

    return AnalyzeResponse(
        terrain_id=req.terrain_id,
        land_profile_id=land_profile_id,
        persisted=persisted,
        parcel=parcel,
        soil=soil,
        weather=weather,
        weather_stats=weather_stats,
        vegetation=vegetation,
        dl_observation=dl_observation,
        neighbors=neighbors,
        crop_recommendations=crop_recommendations_out,
        agro_calc_top_crop=top_crop_agro,
        report=report,
        warnings=warnings,
    )
