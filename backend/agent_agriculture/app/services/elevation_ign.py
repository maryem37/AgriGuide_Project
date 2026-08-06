"""IGN elevation API helper used as a fallback when LiDAR is unavailable."""

from __future__ import annotations

import requests

ELEVATION_URL = "https://data.geopf.fr/altimetrie/1.0/calcul/alti/rest/elevation.json"


def recuperer_elevations(lons: list[float], lats: list[float]) -> list[float]:
    """Fetch altitudes in chunks to avoid overlong URL query strings."""
    if not lons or not lats:
        return []

    chunk_size = 150
    elevations: list[float] = []

    for i in range(0, len(lons), chunk_size):
        chunk_lons = lons[i : i + chunk_size]
        chunk_lats = lats[i : i + chunk_size]
        response = requests.get(
            ELEVATION_URL,
            params={
                "lon": "|".join(str(x) for x in chunk_lons),
                "lat": "|".join(str(y) for y in chunk_lats),
                "resource": "ign_rge_alti_wld",
                "delimiter": "|",
            },
            timeout=10,
        )
        response.raise_for_status()
        elevations.extend(float(p["z"]) for p in response.json().get("elevations", []))

    return elevations
