"""
Section 5/8.2 — soil data. SoilGrids is the always-free default (global
250m grid, no key). Point APIs are queried at the polygon centroid; for
larger parcels, callers should grid-sample (left as a TODO hook below —
not needed for MVP-sized farm parcels).
"""
import httpx
from tenacity import retry, stop_after_attempt, wait_exponential
from config import settings
from schemas import Coordinate, SoilData

_PROPERTIES = ["phh2o", "nitrogen", "soc", "sand", "clay", "silt", "cec", "bdod", "cfvo"]

# SoilGrids returns scaled integers. Divide by these factors to get real units.
# See: https://www.isric.org/explore/soilgrids/faq-soilgrids#What_do_the_units_mean
_SCALE = {
    "phh2o":    10,   # → pH (dimensionless)
    "nitrogen": 100,  # → g/kg
    "soc":      10,   # → g/kg (Soil Organic Carbon)
    "sand":     10,   # → % volume
    "clay":     10,   # → % volume
    "silt":     10,   # → % volume
    "cec":      10,   # → cmolc/kg (Cation Exchange Capacity — proxy for K/P retention)
    "bdod":     100,  # → kg/dm³ (Bulk density)
    "cfvo":     10,   # → % volume (Coarse fragments / stones)
}


@retry(stop=stop_after_attempt(3), wait=wait_exponential(min=1, max=6))
async def _query_soilgrids(lat: float, lon: float) -> dict:
    params = {
        "lon": lon,
        "lat": lat,
        "property": _PROPERTIES,
        "depth": "0-5cm",
        "value": "mean",
    }
    async with httpx.AsyncClient(timeout=15) as client:
        resp = await client.get(settings.soilgrids_base, params=params)
        resp.raise_for_status()
        return resp.json()


def _extract(layers: list[dict], name: str) -> float | None:
    for layer in layers:
        if layer["name"] == name:
            try:
                val = layer["depths"][0]["values"]["mean"]
                factor = _SCALE.get(name, 1)
                return round(val / factor, 3) if val is not None else None
            except (KeyError, IndexError, TypeError):
                return None
    return None


async def get_soil_data(centroid: Coordinate) -> SoilData:
    try:
        raw = await _query_soilgrids(centroid.lat, centroid.lon)
        layers = raw.get("properties", {}).get("layers", [])
        return SoilData(
            source="soilgrids",
            ph=_extract(layers, "phh2o"),
            nitrogen_g_kg=_extract(layers, "nitrogen"),
            organic_carbon_g_kg=_extract(layers, "soc"),
            sand_pct=_extract(layers, "sand"),
            clay_pct=_extract(layers, "clay"),
            silt_pct=_extract(layers, "silt"),
            cec_cmolkg=_extract(layers, "cec"),
            bulk_density_kg_dm3=_extract(layers, "bdod"),
            coarse_fragments_pct=_extract(layers, "cfvo"),
            depth_cm="0-5cm",
        )
    except httpx.HTTPError as e:
        return SoilData(source="unavailable", warning=f"SoilGrids request failed: {e}")


# --- Optional accuracy upgrade hook (INRAE ground-truth) ---
async def get_inrae_groundtruth(centroid: Coordinate) -> SoilData | None:
    """
    Placeholder for INRAE GisSol/RMQS point data. Coverage is sparse, so
    this should only override SoilGrids where a nearby sample exists.
    Not required for MVP — wire in once you have INRAE access details.
    """
    return None