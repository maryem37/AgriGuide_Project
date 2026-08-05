"""
Resolves a rough point to an exact parcel polygon.
Order: cadastre (Etalab API Carto) -> RPG geometries -> manual fallback.

Ported as-is from the standalone `agri-advisor-parcelle` prototype.
"""
import math
import httpx
from collections import Counter
from tenacity import retry, stop_after_attempt, wait_exponential
from shapely.geometry import shape, Point
from app.config import settings
from app.models.schemas import ParcelRequest, ParcelResolution, Coordinate, NeighborParcel, NeighborCropContext
from app.taxonomy import normalize_crop, get_display_name


def _compute_area(poly) -> tuple[float | None, float | None]:
    try:
        # Calculate area of polygon in degrees squared
        area_deg = poly.area
        # Get centroid latitude for projection scaling
        lat_rad = math.radians(poly.centroid.y)
        # 1 degree of lat ~ 111,320m. 1 degree of lon ~ 111,320m * cos(lat)
        # Area in m^2 ~ Area in deg^2 * (111320) * (111320 * cos(lat))
        area_m2 = area_deg * 111320.0 * 111320.0 * math.cos(lat_rad)
        area_m2 = round(area_m2, 1)
        area_ha = round(area_m2 / 10000.0, 2)
        return area_ha, area_m2
    except Exception:
        return None, None


@retry(stop=stop_after_attempt(3), wait=wait_exponential(min=1, max=6))
async def _query_cadastre(lat: float, lon: float) -> dict | None:
    """API Carto cadastre parcelle endpoint - point-in-polygon lookup."""
    url = f"{settings.cadastre_api_base}/parcelle"
    params = {"geom": f'{{"type":"Point","coordinates":[{lon},{lat}]}}', "_limit": 1}
    async with httpx.AsyncClient(timeout=10) as client:
        resp = await client.get(url, params=params)
        resp.raise_for_status()
        data = resp.json()
        features = data.get("features", [])
        return features[0] if features else None


@retry(stop=stop_after_attempt(3), wait=wait_exponential(min=1, max=6))
async def _query_rpg_point(lat: float, lon: float) -> dict | None:
    """RPG (Registre Parcellaire Graphique) WFS - point lookup, gives crop history."""
    url = settings.rpg_wfs_base
    params = {
        "service": "WFS",
        "version": "2.0.0",
        "request": "GetFeature",
        "typeName": "RPG.LATEST:parcelles_graphiques",
        "outputFormat": "application/json",
        # NOTE: data.geopf.fr WFS uses latitude-first axis order (CRS84/EPSG:4326
        # with axis-order as declared). POINT must be (lat lon), NOT (lon lat).
        "cql_filter": f"INTERSECTS(geom, POINT({lat} {lon}))",
        "count": 1,
    }
    async with httpx.AsyncClient(timeout=10) as client:
        resp = await client.get(url, params=params)
        resp.raise_for_status()
        data = resp.json()
        features = data.get("features", [])
        return features[0] if features else None


@retry(stop=stop_after_attempt(3), wait=wait_exponential(min=1, max=6))
async def _query_rpg_bbox(lat: float, lon: float, radius_m: float) -> list[dict]:
    """
    RPG WFS - bounding-box lookup for neighboring declared parcels.
    Converts a meter radius to a rough degree bbox (good enough at
    field scale; not geodesically precise, which doesn't matter here).
    """
    lat_delta = radius_m / 111_000
    lon_delta = radius_m / (111_000 * math.cos(math.radians(lat)))
    min_lat, max_lat = lat - lat_delta, lat + lat_delta
    min_lon, max_lon = lon - lon_delta, lon + lon_delta

    url = settings.rpg_wfs_base
    params = {
        "service": "WFS",
        "version": "2.0.0",
        "request": "GetFeature",
        "typeName": "RPG.LATEST:parcelles_graphiques",
        "outputFormat": "application/json",
        # NOTE: same axis-order issue — BBOX must be (min_lat, min_lon, max_lat, max_lon).
        "cql_filter": f"BBOX(geom, {min_lat}, {min_lon}, {max_lat}, {max_lon})",
        "count": 200,  # cap so a dense agricultural area doesn't return unbounded results
    }
    async with httpx.AsyncClient(timeout=15) as client:
        resp = await client.get(url, params=params)
        resp.raise_for_status()
        data = resp.json()
        return data.get("features", [])


async def resolve_parcel(req: ParcelRequest) -> ParcelResolution:
    lat, lon = req.point.lat, req.point.lon

    # 1. Try cadastre first (most precise legal boundary)
    try:
        feature = await _query_cadastre(lat, lon)
        if feature:
            geom = feature["geometry"]
            poly = shape(geom)
            props = feature.get("properties", {})

            # Cross-check against RPG to flag whether this is actually
            # registered farmland, since cadastre alone covers urban
            # land too. Not a hard block — fallow/undeclared land can
            # still be real farmland — but a clear signal either way.
            is_agricultural = None
            agri_note = None
            rpg_id_parcel = None
            crop_declared = None

            try:
                rpg_match = await _query_rpg_point(lat, lon)
                if rpg_match:
                    rpg_props = rpg_match.get("properties", {})
                    is_agricultural = True
                    agri_note = "Parcelle trouvée dans le registre RPG (culture déclarée par un agriculteur)."
                    rpg_id_parcel = rpg_props.get("id_parcel")

                    code_cultu = rpg_props.get("code_cultu")
                    if code_cultu:
                        crop_declared = get_display_name(normalize_crop(code_cultu))
                else:
                    is_agricultural = False
                    agri_note = (
                        "Aucune déclaration RPG trouvée à cet endroit — cette parcelle n'est "
                        "probablement pas exploitée comme terre agricole actuellement (zone "
                        "urbaine, forêt, friche, ou terre non déclarée). Vérifiez avant de "
                        "continuer si vous ciblez une exploitation agricole active."
                    )
            except httpx.HTTPError:
                agri_note = "Impossible de vérifier le statut agricole (RPG indisponible) — non vérifié."

            area_ha, area_m2 = _compute_area(poly)
            return ParcelResolution(
                resolved=True,
                source="cadastre",
                geometry=geom,
                centroid=Coordinate(lat=poly.centroid.y, lon=poly.centroid.x),
                parcel_id=props.get("idu"),
                rpg_id_parcel=rpg_id_parcel,
                crop_declared=crop_declared,
                area_ha=area_ha,
                area_m2=area_m2,
                is_agricultural=is_agricultural,
                agricultural_note=agri_note,
            )
    except httpx.HTTPError:
        pass  # fall through to RPG rather than failing the whole request

    # 2. Try RPG directly (also gives declared crop history) — if we land
    #    here, the parcel IS in RPG by definition, so it's agricultural.
    try:
        feature = await _query_rpg_point(lat, lon)
        if feature:
            geom = feature["geometry"]
            poly = shape(geom)
            props = feature.get("properties", {})
            area_ha, area_m2 = _compute_area(poly)
            return ParcelResolution(
                resolved=True,
                source="rpg",
                geometry=geom,
                centroid=Coordinate(lat=poly.centroid.y, lon=poly.centroid.x),
                parcel_id=props.get("id_parcel"),
                rpg_id_parcel=props.get("id_parcel"),
                area_ha=area_ha,
                area_m2=area_m2,
                crop_declared=get_display_name(normalize_crop(props.get("code_cultu"))),
                is_agricultural=True,
                agricultural_note="Parcelle trouvée directement dans le registre RPG.",
            )
    except httpx.HTTPError:
        pass

    # 3. Manual boundary supplied by the user
    if req.manual_geojson:
        poly = shape(req.manual_geojson)
        area_ha, area_m2 = _compute_area(poly)
        return ParcelResolution(
            resolved=True,
            source="manual",
            geometry=req.manual_geojson,
            centroid=Coordinate(lat=poly.centroid.y, lon=poly.centroid.x),
            area_ha=area_ha,
            area_m2=area_m2,
            warning="Manual boundary — not verified against cadastre/RPG.",
        )

    # 4. Nothing worked — surface this loudly, never silently fall back to a point
    return ParcelResolution(
        resolved=False,
        source="unresolved",
        centroid=req.point,
        warning=(
            "No parcel boundary found. Downstream data will NOT be "
            "parcel-specific until a boundary is drawn manually."
        ),
    )


async def get_neighboring_crop_context(
    centroid: Coordinate, radius_m: float = 15_000, exclude_parcel_id: str | None = None
) -> NeighborCropContext:
    """
    Pulls declared crops for RPG parcels within radius_m of the given
    point, and computes what percentage of neighbors grew each crop.
    Count-based percentage (share of parcels), not area-weighted — a
    simplification worth knowing: a few large neighboring fields could
    outweigh many small ones in real agronomic impact.
    """
    try:
        features = await _query_rpg_bbox(centroid.lat, centroid.lon, radius_m)
    except httpx.HTTPError as e:
        return NeighborCropContext(
            neighbor_count=0,
            crop_distribution_pct={},
            neighbors=[],
            note=f"Impossible de récupérer les parcelles voisines (RPG indisponible: {e}).",
        )

    neighbors = []
    crop_codes = []
    for feat in features:
        props = feat.get("properties", {})
        pid = props.get("id_parcel")
        if exclude_parcel_id and pid == exclude_parcel_id:
            continue  # don't count the selected parcel as its own neighbor
        code = normalize_crop(props.get("code_cultu"))
        neighbors.append(NeighborParcel(geometry=feat["geometry"], crop_code=code))
        if code:
            crop_codes.append(code)

    distribution = {}
    if crop_codes:
        counts = Counter(crop_codes)
        total = len(crop_codes)
        distribution = {get_display_name(code): round(100 * n / total, 1) for code, n in counts.most_common()}

    return NeighborCropContext(
        neighbor_count=len(neighbors),
        crop_distribution_pct=distribution,
        neighbors=neighbors,
        note=(
            f"{len(neighbors)} parcelle(s) RPG trouvée(s) dans un rayon de "
            f"{(radius_m / 1000):.0f} km. "
            if radius_m >= 1000
            else f"{len(neighbors)} parcelle(s) RPG trouvée(s) dans un rayon de {int(radius_m)} m. "
        )
        + "Pourcentages calculés par nombre de parcelles, pas par surface.",
    )
