"""Encode elevation and index rasters into web-native textures.

Produces:
  - Mapbox Terrain-RGB PNG for elevation (consumed by deck.gl's
    `TerrainLayer` via `elevationDecoder`).
  - Colour-ramp PNG textures for NDVI / NDWI / NDMI / slope, so the
    frontend can swap the draped texture without re-deriving colours in JS.

Kept separate from relief_payload.py, which stays focused on data
acquisition; this module only turns already-computed grids into images.
"""
from __future__ import annotations

import base64
from io import BytesIO

import numpy as np
from PIL import Image

# Mapbox Terrain-RGB encoding: height = -10000 + (R*256*256 + G*256 + B) * 0.1
_TERRAIN_RGB_OFFSET = -10000.0
_TERRAIN_RGB_SCALE = 0.1


def _to_data_url(img: Image.Image) -> str:
    buf = BytesIO()
    img.save(buf, format="PNG")
    b64 = base64.b64encode(buf.getvalue()).decode("ascii")
    return f"data:image/png;base64,{b64}"


def encode_terrain_rgb(elevation: np.ndarray, valid: np.ndarray) -> str:
    """Encode an elevation grid as a Mapbox Terrain-RGB PNG data URL.

    Cells outside `valid` inherit the nearest valid elevation (simple
    nearest-neighbour fill) instead of an arbitrary default, so deck.gl
    never renders a fabricated cliff at the parcel edge. The frontend still
    clips visually using `grille_validite` — this fill only keeps the mesh
    itself well-behaved.
    """
    elev = elevation.astype(np.float64).copy()

    if valid.any() and not valid.all():
        from scipy.ndimage import distance_transform_edt

        _, indices = distance_transform_edt(~valid, return_indices=True)
        elev = elev[tuple(indices)]
    elif not valid.any():
        elev[:] = 0.0

    quantized = np.round((elev - _TERRAIN_RGB_OFFSET) / _TERRAIN_RGB_SCALE).astype(np.uint32)
    quantized = np.clip(quantized, 0, 256**3 - 1)

    r = (quantized >> 16) & 0xFF
    g = (quantized >> 8) & 0xFF
    b = quantized & 0xFF
    rgb = np.dstack([r, g, b]).astype(np.uint8)

    return _to_data_url(Image.fromarray(rgb, mode="RGB"))


def _diverging_ramp(value: np.ndarray, vmin: float, vmax: float) -> np.ndarray:
    """Blue -> beige -> green ramp for NDVI/NDWI/NDMI (domain ~[-1, 1])."""
    t = np.clip((value - vmin) / max(vmax - vmin, 1e-6), 0.0, 1.0)
    stops = np.array(
        [
            [43, 79, 145],    # low
            [230, 220, 180],  # mid
            [26, 122, 63],    # high
        ],
        dtype=np.float64,
    )
    t2 = t * 2.0
    lower = t2 <= 1.0
    out = np.empty(value.shape + (3,), dtype=np.float64)
    out[lower] = stops[0] + (stops[1] - stops[0]) * t2[lower][:, None]
    out[~lower] = stops[1] + (stops[2] - stops[1]) * (t2[~lower] - 1.0)[:, None]
    return out


def _sequential_ramp(value: np.ndarray, vmin: float, vmax: float) -> np.ndarray:
    """Pale -> dark amber ramp, used for slope percentage."""
    t = np.clip((value - vmin) / max(vmax - vmin, 1e-6), 0.0, 1.0)
    low = np.array([245, 240, 225], dtype=np.float64)
    high = np.array([160, 60, 20], dtype=np.float64)
    return low + (high - low) * t[..., None]


def colorize_index(
    grid: np.ndarray,
    valid: np.ndarray,
    vmin: float,
    vmax: float,
    ramp: str = "diverging",
    nodata_rgb: tuple[int, int, int] = (60, 60, 60),
) -> str:
    """Colorize a scalar grid (NDVI/NDWI/NDMI/slope) into a PNG data URL.

    Invalid/masked cells are painted a flat neutral grey — never a value
    derived from interpolation — matching the "zones grises" legend already
    shown in the viewer.
    """
    ramp_fn = _diverging_ramp if ramp == "diverging" else _sequential_ramp
    rgb = ramp_fn(grid.astype(np.float64), vmin, vmax)
    rgb[~valid] = nodata_rgb
    img = Image.fromarray(np.clip(rgb, 0, 255).astype(np.uint8), mode="RGB")
    return _to_data_url(img)
