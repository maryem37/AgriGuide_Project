"""
Orchestrator. This is the "agent" from Section 4 — currently a fixed
parallel-then-sequential flow rather than a true tool-calling agent
loop, which is the right MVP simplification (Section 11): same data
contracts, easy to swap in real agentic tool-selection later without
changing any service module.
"""
import asyncio
from pathlib import Path
from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from fastapi.responses import FileResponse
from pydantic import BaseModel
from schemas import (
    ParcelRequest,
    ParcelResolution,
    AdvisorReport,
    NeighborCropContext,
    AgroCalcEstimate,
    SoilData,
    WeatherData,
    VegetationData,
    DLCropObservation,
)
from services import parcel_service, soil_service, weather_service, satellite_service, ml_service, rag_service, synthesis_service, dl_service, agro_calc_service

app = FastAPI(title="AI Agricultural Advisor")

# CORS: the React dev server (Vite) runs on a different origin
# (localhost:5173) than this API (127.0.0.1:8000), so the browser blocks
# every request unless the API explicitly allows it. Add your production
# frontend origin here too once you deploy (e.g. "https://your-domain.com") —
# never use allow_origins=["*"] together with allow_credentials=True.
app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:5173", "http://127.0.0.1:5173"],
    allow_methods=["*"],
    allow_headers=["*"],
)

_STATIC_DIR = Path(__file__).parent / "static"
_STATIC_DIR.mkdir(exist_ok=True)
app.mount("/static", StaticFiles(directory=str(_STATIC_DIR)), name="static")


@app.get("/")
async def root():
    return FileResponse(str(_STATIC_DIR / "index.html"))


@app.post("/parcel/resolve", response_model=ParcelResolution)
async def resolve_parcel_only(req: ParcelRequest):
    return await parcel_service.resolve_parcel(req)


@app.post("/parcel/neighbors", response_model=NeighborCropContext)
async def get_neighbors(req: ParcelRequest, radius_m: float = 800):
    parcel = await parcel_service.resolve_parcel(req)
    centroid = parcel.centroid or req.point
    return await parcel_service.get_neighboring_crop_context(
        centroid, radius_m=radius_m, exclude_parcel_id=parcel.rpg_id_parcel
    )


# --- NDVI heatmap (for the frontend's map overlay toggle) ---
# NOTE: this depends on a new satellite_service.get_ndvi_heatmap(geometry)
# function that does not exist in the satellite_service.py reviewed so far.
# get_ndvi() only returns an aggregate mean_ndvi (via Sentinel Hub's
# Statistics API) — a pixel-level heatmap image needs the Process API
# instead, rendered to a PNG and base64-encoded. Until that function is
# added, this route fails loudly with a 501 rather than silently returning
# nothing, so the failure is obvious rather than a mysterious blank map.
class NdviHeatmapBounds(BaseModel):
    south: float
    west: float
    north: float
    east: float


class NdviHeatmapResponse(BaseModel):
    image_base64: str
    bounds: NdviHeatmapBounds


@app.post("/parcel/ndvi_heatmap", response_model=NdviHeatmapResponse)
async def get_ndvi_heatmap(req: ParcelRequest):
    parcel = await parcel_service.resolve_parcel(req)
    if not parcel.resolved or not parcel.geometry:
        raise HTTPException(
            status_code=422,
            detail=parcel.warning or "Impossible de résoudre une géométrie de parcelle pour la carte NDVI.",
        )
    try:
        heatmap_func = satellite_service.get_ndvi_heatmap
    except AttributeError:
        raise HTTPException(
            status_code=501,
            detail=(
                "satellite_service.get_ndvi_heatmap() n'est pas encore implémenté. "
                "get_ndvi() ne renvoie qu'une statistique agrégée (mean_ndvi), pas une "
                "image pixel par pixel — il faut une fonction séparée appelant l'API "
                "Process de Sentinel Hub (pas Statistics) et encodant le résultat en PNG base64."
            ),
        )
    return await heatmap_func(parcel.geometry)


@app.post("/advise", response_model=AdvisorReport)
async def advise(req: ParcelRequest):
    parcel = await parcel_service.resolve_parcel(req)
    if not parcel.resolved:
        raise HTTPException(
            status_code=422,
            detail=parcel.warning or "Could not resolve a parcel boundary.",
        )

    # Satellite NDVI and the DL classifier both need the actual polygon
    # (not just centroid), so they only run if we have geometry — fall
    # back gracefully otherwise, same pattern for both.
    #
    # return_exceptions=True is required here: soil_service and
    # weather_service already catch their own httpx errors internally and
    # always return a valid (possibly "unavailable") object, but
    # satellite_service.get_ndvi() and dl_service.predict_crop() do not
    # have that same internal guard against *unexpected* exceptions
    # (a parsing bug, a timeout not raised as httpx.HTTPError, etc.).
    # Without return_exceptions=True, one bad response from either of
    # those would raise inside gather() and take down the ENTIRE /advise
    # request — including the soil and weather data that already
    # succeeded — which contradicts this project's own "degrade
    # gracefully" principle (see README §7, §6).
    results = await asyncio.gather(
        soil_service.get_soil_data(parcel.centroid),
        weather_service.get_weather_data(parcel.centroid),
        satellite_service.get_ndvi(parcel.geometry) if parcel.geometry else asyncio.sleep(0, result=None),
        dl_service.predict_crop(parcel.geometry) if parcel.geometry else asyncio.sleep(0, result=None),
        return_exceptions=True,
    )
    soil, weather, vegetation, dl_observation = results

    if isinstance(soil, Exception):
        soil = SoilData(
            source="unavailable",
            warning=f"Erreur inattendue lors de la récupération des données de sol : {soil}",
        )
    if isinstance(weather, Exception):
        weather = WeatherData(
            source="unavailable",
            warning=f"Erreur inattendue lors de la récupération des données météo : {weather}",
        )
    if vegetation is None:
        vegetation = VegetationData(source="unavailable", warning="No parcel geometry available for satellite lookup.")
    elif isinstance(vegetation, Exception):
        vegetation = VegetationData(source="unavailable", warning=f"Erreur inattendue NDVI : {vegetation}")
    if dl_observation is None:
        dl_observation = DLCropObservation(source="unavailable", warning="No parcel geometry available for satellite lookup.")
    elif isinstance(dl_observation, Exception):
        dl_observation = DLCropObservation(source="unavailable", warning=f"Erreur inattendue classification DL : {dl_observation}")

    crop_recs = ml_service.recommend_crops(soil, weather)
    top_crop = crop_recs[0].crop if crop_recs else None

    agro_calc = (
        agro_calc_service.estimate_fertilizer_and_irrigation(top_crop, soil, weather)
        if top_crop else AgroCalcEstimate(crop="", warning="Aucune culture recommandée disponible.")
    )

    # rag_service.retrieve() is synchronous (it calls the blocking Mistral
    # embed SDK under the hood) — run it in a worker thread so it doesn't
    # block the asyncio event loop for every other request/user.
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

    synthesis = await synthesis_service.synthesize_stage1(parcel, soil, weather, crop_recs, chunks, vegetation, dl_observation, agro_calc)
    report = await synthesis_service.generate_report(synthesis, parcel)

    return report


@app.get("/health")
async def health():
    return {"status": "ok"}