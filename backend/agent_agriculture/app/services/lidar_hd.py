"""Access to IGN LiDAR HD DTM (terrain model) for reliable relief rendering."""

from __future__ import annotations

from hashlib import sha256
from io import BytesIO
import json
from pathlib import Path
import time
from urllib.parse import parse_qs, urlparse

import numpy as np
import requests
import tifffile
from pyproj import Transformer

WFS_URL = "https://data.geopf.fr/wfs/ows"
WMS_URL = "https://data.geopf.fr/wms-r/wms"
WFS_LAYER = "IGNF_MNT-LIDAR-HD:dalle"
WMS_LAYER = "IGNF_LIDAR-HD_MNT_ELEVATION.ELEVATIONGRIDCOVERAGE.LAMB93"
CACHE_DIR = Path(__file__).resolve().parent.parent / "terrain_data" / "lidar_cache"


def _cache_path(bbox_2154: tuple[float, float, float, float], width: int, height: int) -> Path:
    key = sha256(f"{bbox_2154!r}:{width}:{height}".encode()).hexdigest()[:20]
    return CACHE_DIR / f"mnt_lidar_{key}.tif"


def _requete_ign(url: str, params: dict | None = None) -> bytes | None:
    """Read a GeoTIFF from IGN with retries on transient gateway errors."""
    for attempt in range(2):
        try:
            response = requests.get(
                url,
                params={**(params or {}), "_cache_bust": str(time.time_ns())},
                timeout=12,
                headers={"Cache-Control": "no-cache"},
            )
        except requests.RequestException:
            if attempt == 0:
                time.sleep(0.5)
                continue
            return None
        if response.ok and response.content[:2] in (b"II", b"MM"):
            return response.content
        if attempt == 0 and (response.status_code in (400, 502, 503, 504) or b"LayerNotDefined" in response.content):
            time.sleep(0.5)
            continue
        return None
    return None


def _reprojeter_dalle(
    content: bytes,
    tile_url: str,
    target_bbox: tuple[float, float, float, float],
    width: int,
    height: int,
) -> np.ndarray:
    """Extract the nearest neighbor target footprint from a tile GeoTIFF."""
    source = np.squeeze(tifffile.imread(BytesIO(content))).astype(float)
    if source.ndim != 2:
        raise RuntimeError("Unexpected LiDAR HD tile format.")

    params = parse_qs(urlparse(tile_url).query)
    xmin, ymin, xmax, ymax = (float(v) for v in params["BBOX"][0].split(","))
    target_xmin, target_ymin, target_xmax, target_ymax = target_bbox

    xs = np.linspace(target_xmin, target_xmax, width)
    ys = np.linspace(target_ymax, target_ymin, height)
    ix = np.clip(np.rint((xs - xmin) / (xmax - xmin) * (source.shape[1] - 1)).astype(int), 0, source.shape[1] - 1)
    iy = np.clip(np.rint((ymax - ys) / (ymax - ymin) * (source.shape[0] - 1)).astype(int), 0, source.shape[0] - 1)
    return source[np.ix_(iy, ix)]


def recuperer_mnt_lidar_hd(geometry_geojson: dict, max_dimension: int = 256) -> dict:
    """Return an IGN LiDAR HD DTM grid over the parcel footprint."""
    from shapely.geometry import shape

    parcel = shape(geometry_geojson)
    min_lon, min_lat, max_lon, max_lat = parcel.bounds

    wfs_params = {
        "SERVICE": "WFS",
        "VERSION": "2.0.0",
        "REQUEST": "GetFeature",
        "TYPENAMES": WFS_LAYER,
        "OUTPUTFORMAT": "application/json",
        "SRSNAME": "EPSG:4326",
        "BBOX": f"{min_lon},{min_lat},{max_lon},{max_lat},EPSG:4326",
    }
    response_wfs = requests.get(WFS_URL, params=wfs_params, timeout=10)
    response_wfs.raise_for_status()
    features = response_wfs.json().get("features", [])
    if not features:
        raise LookupError("IGN LiDAR HD DTM is not published on this parcel.")

    projection = Transformer.from_crs("EPSG:4326", "EPSG:2154", always_xy=True)
    min_x, min_y = projection.transform(min_lon, min_lat)
    max_x, max_y = projection.transform(max_lon, max_lat)
    width_m, height_m = max_x - min_x, max_y - min_y

    pixel_size_m = max(0.5, width_m / (max_dimension - 1), height_m / (max_dimension - 1))
    width = max(2, int(np.ceil(width_m / pixel_size_m)) + 1)
    height = max(2, int(np.ceil(height_m / pixel_size_m)) + 1)

    bbox_2154 = (min_x, min_y, max_x, max_y)
    cache = _cache_path(bbox_2154, width, height)

    if cache.exists():
        content = cache.read_bytes()
    else:
        CACHE_DIR.mkdir(parents=True, exist_ok=True)
        wms_params = {
            "SERVICE": "WMS",
            "VERSION": "1.3.0",
            "REQUEST": "GetMap",
            "LAYERS": WMS_LAYER,
            "STYLES": "",
            "FORMAT": "image/geotiff",
            "CRS": "IGNF:LAMB93",
            "BBOX": ",".join(f"{v:.3f}" for v in bbox_2154),
            "WIDTH": width,
            "HEIGHT": height,
        }
        content = _requete_ign(WMS_URL, wms_params)

        if content is None and len(features) == 1:
            tile_url = features[0].get("properties", {}).get("url")
            if tile_url:
                tile_content = _requete_ign(tile_url)
                if tile_content is not None:
                    tile_elevation = _reprojeter_dalle(tile_content, tile_url, bbox_2154, width, height)
                    out = BytesIO()
                    tifffile.imwrite(out, tile_elevation.astype(np.float32))
                    content = out.getvalue()

        if content is None:
            raise LookupError(
                "LiDAR HD is referenced on this parcel, but IGN service is temporarily unavailable. Try again shortly."
            )

        cache.write_bytes(content)

    elevation = np.squeeze(tifffile.imread(BytesIO(content))).astype(float)
    if elevation.ndim != 2:
        raise RuntimeError("Unexpected LiDAR HD format.")

    valid = np.isfinite(elevation) & (elevation > -9990) & (elevation < 10000)
    if not valid.any():
        raise LookupError("LiDAR HD contains no usable altitude on this parcel.")

    elevation = np.where(valid, elevation, float(np.median(elevation[valid])))

    props = features[0].get("properties", {})
    metadata = props.get("metadata", "{}")
    try:
        metadata = json.loads(metadata) if isinstance(metadata, str) else metadata
    except json.JSONDecodeError:
        metadata = {}

    return {
        "elevation": elevation,
        "validite": valid,
        "largeur_m": width_m,
        "hauteur_m": height_m,
        "resolution_m": round(pixel_size_m, 2),
        "date_acquisition": metadata.get("date_fin_acquisition") or props.get("timestamp"),
        "source": "IGN LiDAR HD - DTM",
    }
