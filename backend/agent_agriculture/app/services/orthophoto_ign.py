"""IGN orthophoto retrieval for realistic texture mapping on 3D relief."""

from __future__ import annotations

import base64

import requests
from pyproj import Geod

WMS_URL = "https://data.geopf.fr/wms-r/wms"
WMS_LAYER = "ORTHOIMAGERY.ORTHOPHOTOS"

_GEOD = Geod(ellps="WGS84")


def _try_wms_request(params: dict) -> requests.Response | None:
    """Return None when response is not a usable image, to try another variant."""
    response = requests.get(WMS_URL, params=params, timeout=30)
    content_type = response.headers.get("Content-Type", "")
    if (
        response.ok
        and response.content
        and not content_type.startswith("application/vnd.ogc")
        and not content_type.startswith("text/xml")
    ):
        return response
    return None


def recuperer_orthophoto_ign(
    min_lon: float,
    min_lat: float,
    max_lon: float,
    max_lat: float,
    largeur_px: int = 1024,
) -> str:
    """Return IGN orthophoto for bbox as a JPEG base64 data URL.

    The pixel aspect ratio is derived from metric ground distances (via
    geodesic length) rather than raw degree deltas.  Longitude degrees
    compress with latitude, so a degree-based ratio would stretch the
    texture vertically when draped on the metric terrain mesh.
    """
    _, _, width_m = _GEOD.inv(min_lon, min_lat, max_lon, min_lat)
    _, _, height_m = _GEOD.inv(min_lon, min_lat, min_lon, max_lat)
    ratio = height_m / max(width_m, 1e-9)
    hauteur_px = max(64, min(2048, int(largeur_px * ratio)))

    base = {
        "SERVICE": "WMS",
        "REQUEST": "GetMap",
        "LAYERS": WMS_LAYER,
        "FORMAT": "image/jpeg",
        "WIDTH": largeur_px,
        "HEIGHT": hauteur_px,
    }

    variants = [
        {**base, "VERSION": "1.3.0", "CRS": "EPSG:4326", "STYLES": "", "BBOX": f"{min_lat},{min_lon},{max_lat},{max_lon}"},
        {**base, "VERSION": "1.3.0", "CRS": "EPSG:4326", "STYLES": "", "BBOX": f"{min_lon},{min_lat},{max_lon},{max_lat}"},
        {**base, "VERSION": "1.1.1", "SRS": "EPSG:4326", "STYLES": "", "BBOX": f"{min_lon},{min_lat},{max_lon},{max_lat}"},
        {**base, "VERSION": "1.1.1", "SRS": "EPSG:4326", "STYLES": "normal", "BBOX": f"{min_lon},{min_lat},{max_lon},{max_lat}"},
    ]

    last_error = None
    for params in variants:
        try:
            response = _try_wms_request(params)
        except requests.RequestException as exc:
            last_error = exc
            continue
        if response is not None:
            image_base64 = base64.b64encode(response.content).decode("ascii")
            return f"data:image/jpeg;base64,{image_base64}"

    raise RuntimeError(
        "IGN orthophoto service did not return a usable image for this footprint."
        + (f" Last network error: {last_error}" if last_error else "")
    )
