"""
Vegetation index (NDVI) from Sentinel-2 via the Copernicus Data Space
Ecosystem Statistical API. This is real satellite-derived data computed
via band math, NOT a trained model — the CNN land-cover/crop-type
classifier is `dl_service.py`, a separate, later phase.

Important honesty note: NDVI reflects whatever is CURRENTLY on the
ground right now (bare soil post-harvest, an actively growing crop,
weeds on fallow land) — it does not by itself say which crop SHOULD be
planted. It's reported as descriptive context (confirms active
vegetation, flags a stressed/bare parcel) rather than fed into crop
suitability scoring, since doing the latter without justification would
be exactly the kind of unfounded number this project's grounding rules
are meant to prevent.

Auth: OAuth2 client-credentials flow. Free account required at
https://dataspace.copernicus.eu — then create an OAuth client under
your account dashboard (User Settings -> OAuth clients) for
SENTINEL_HUB_CLIENT_ID / SENTINEL_HUB_CLIENT_SECRET in the root `.env`
(named after Sentinel Hub, the API surface this OAuth client actually
authenticates against — same Copernicus Data Space Ecosystem account
either way).

Ported from the standalone `agri-advisor-parcelle` prototype — only the
settings field names changed (copernicus_client_id/secret ->
sentinel_hub_client_id/secret) to match this repo's `.env.example`.
"""
import base64
import time
from datetime import datetime, timedelta, timezone
import httpx
from tenacity import retry, stop_after_attempt, wait_exponential
from app.config import settings
from app.models.schemas import VegetationData

_TOKEN_URL = "https://identity.dataspace.copernicus.eu/auth/realms/CDSE/protocol/openid-connect/token"
_STATISTICS_URL = "https://sh.dataspace.copernicus.eu/statistics/v1"
_PROCESS_URL = "https://sh.dataspace.copernicus.eu/api/v1/process"

# SCL (Scene Classification Layer) codes excluded from the NDVI mean:
# 3=cloud shadow, 8/9=cloud medium/high probability, 10=thin cirrus, 11=snow
_NDVI_EVALSCRIPT = """
//VERSION=3
function setup() {
  return {
    input: [{ bands: ["B04", "B08", "SCL", "dataMask"] }],
    output: [
      { id: "data", bands: ["ndvi"] },
      { id: "dataMask", bands: 1 }
    ]
  }
}
function evaluatePixel(samples) {
  let ndvi = (samples.B08 - samples.B04) / (samples.B08 + samples.B04 + 1e-6);
  let bad = (samples.SCL == 3 || samples.SCL == 8 || samples.SCL == 9 || samples.SCL == 10 || samples.SCL == 11);
  let mask = bad ? 0 : samples.dataMask;
  return { data: [ndvi], dataMask: [mask] };
}
"""

_token_cache = {"token": None, "expires_at": 0.0}


def _pixel_dims_for_resolution(geometry: dict, target_resolution_m: float) -> tuple[int, int]:
    """
    Computes width/height IN PIXELS for a target meters-per-pixel
    resolution — NOT resx/resy in meters.

    Sentinel Hub's resx/resy parameters are interpreted in the bounds'
    CRS units. Since this project's bounds use CRS84 (plain lat/lon
    degrees), "resx: 10" was silently being read as 10 DEGREES
    (~1,100km), not 10 meters — collapsing every request's polygon,
    regardless of real size, into a single oversized pixel. L1C's
    resolution ceiling caught this with a 400 ("444.91 meters per
    pixel exceeds the limit"); L2A (get_ndvi) has no such ceiling and
    was silently returning a real-looking but wrong single-pixel
    average instead of a genuine 10m grid. Same conversion constant
    already used in services/parcel_service.py's _compute_area, for
    consistency.
    """
    from shapely.geometry import shape
    import math

    poly = shape(geometry)
    minx, miny, maxx, maxy = poly.bounds  # lon/lat degrees
    lat_rad = math.radians(poly.centroid.y)
    width_m = (maxx - minx) * 111320.0 * math.cos(lat_rad)
    height_m = (maxy - miny) * 111320.0

    width_px = max(1, round(width_m / target_resolution_m))
    height_px = max(1, round(height_m / target_resolution_m))
    return width_px, height_px


@retry(stop=stop_after_attempt(3), wait=wait_exponential(min=1, max=6))
async def _get_access_token() -> str:
    """OAuth2 client-credentials flow, cached in-process until near expiry."""
    if _token_cache["token"] and time.time() < _token_cache["expires_at"] - 30:
        return _token_cache["token"]

    async with httpx.AsyncClient(timeout=15) as client:
        resp = await client.post(
            _TOKEN_URL,
            data={
                "grant_type": "client_credentials",
                "client_id": settings.sentinel_hub_client_id,
                "client_secret": settings.sentinel_hub_client_secret,
            },
        )
        resp.raise_for_status()
        data = resp.json()

    _token_cache["token"] = data["access_token"]
    _token_cache["expires_at"] = time.time() + data.get("expires_in", 600)
    return _token_cache["token"]


@retry(stop=stop_after_attempt(3), wait=wait_exponential(min=1, max=6))
async def get_ndvi(geometry: dict, days_back: int = 30) -> VegetationData:
    """
    Mean NDVI over the parcel polygon for the last `days_back` days,
    using Sentinel-2 L2A with cloud/shadow/snow pixels masked out via
    the Scene Classification Layer before averaging.
    """
    if not settings.sentinel_hub_client_id or not settings.sentinel_hub_client_secret:
        return VegetationData(
            source="unavailable",
            warning=(
                "Sentinel Hub credentials not set. Create a free account at "
                "dataspace.copernicus.eu and an OAuth client, then set "
                "SENTINEL_HUB_CLIENT_ID / SENTINEL_HUB_CLIENT_SECRET in .env."
            ),
        )

    try:
        token = await _get_access_token()
    except httpx.HTTPError as e:
        return VegetationData(source="unavailable", warning=f"Copernicus auth failed: {e}")

    end = datetime.now(timezone.utc)
    start = end - timedelta(days=days_back)
    _ndvi_width_px, _ndvi_height_px = _pixel_dims_for_resolution(geometry, target_resolution_m=10)

    payload = {
        "input": {
            "bounds": {
                "geometry": geometry,
                "properties": {"crs": "http://www.opengis.net/def/crs/OGC/1.3/CRS84"},
            },
            "data": [
                {
                    "type": "sentinel-2-l2a",
                    "dataFilter": {"maxCloudCoverage": 60, "mosaickingOrder": "leastCC"},
                }
            ],
        },
        "aggregation": {
            "timeRange": {
                "from": start.strftime("%Y-%m-%dT%H:%M:%SZ"),
                "to": end.strftime("%Y-%m-%dT%H:%M:%SZ"),
            },
            "aggregationInterval": {"of": f"P{days_back}D"},
            "evalscript": _NDVI_EVALSCRIPT,
            "width": _ndvi_width_px,
            "height": _ndvi_height_px,
        },
    }

    try:
        async with httpx.AsyncClient(timeout=30) as client:
            resp = await client.post(
                _STATISTICS_URL,
                json=payload,
                headers={"Authorization": f"Bearer {token}", "Content-Type": "application/json"},
            )
            if resp.status_code >= 400:
                return VegetationData(
                    source="unavailable",
                    warning=f"Sentinel Hub statistics request failed: {resp.status_code} — {resp.text[:1000]}",
                )
            data = resp.json()
    except httpx.HTTPError as e:
        return VegetationData(source="unavailable", warning=f"Sentinel Hub statistics request failed: {e}")

    try:
        buckets = data.get("data", [])
        if not buckets:
            return VegetationData(
                source="sentinel-2",
                warning=f"No cloud-free Sentinel-2 coverage found in the last {days_back} days for this parcel.",
            )
        stats = buckets[0]["outputs"]["data"]["bands"]["ndvi"]["stats"]
        mean_ndvi = stats.get("mean")
        valid_count = stats.get("sampleCount", 0)

        if mean_ndvi is None or not valid_count:
            return VegetationData(
                source="sentinel-2",
                warning=f"No valid cloud-free pixels found in the last {days_back} days for this parcel.",
            )

        return VegetationData(
            source="sentinel-2",
            mean_ndvi=round(mean_ndvi, 4),
            observation_window_days=days_back,
            valid_pixel_count=valid_count,
        )
    except (KeyError, IndexError, TypeError) as e:
        return VegetationData(source="unavailable", warning=f"Unexpected Sentinel Hub response shape: {e}")


_NDVI_HEATMAP_EVALSCRIPT = """
//VERSION=3
function setup() {
  return {
    input: [{ bands: ["B04", "B08", "SCL", "dataMask"] }],
    output: { bands: 4, sampleType: "UINT8" }
  };
}

var ramp = [
  [-0.2, [165, 0, 38]],
  [0.0,  [215, 48, 39]],
  [0.2,  [244, 109, 67]],
  [0.35, [254, 224, 139]],
  [0.5,  [217, 239, 139]],
  [0.65, [102, 189, 99]],
  [0.8,  [26, 152, 80]],
  [1.0,  [0, 104, 55]]
];

function rampColor(ndvi) {
  if (ndvi <= ramp[0][0]) return ramp[0][1];
  for (var i = 1; i < ramp.length; i++) {
    if (ndvi <= ramp[i][0]) {
      var lo = ramp[i - 1], hi = ramp[i];
      var t = (ndvi - lo[0]) / (hi[0] - lo[0]);
      return [
        Math.round(lo[1][0] + t * (hi[1][0] - lo[1][0])),
        Math.round(lo[1][1] + t * (hi[1][1] - lo[1][1])),
        Math.round(lo[1][2] + t * (hi[1][2] - lo[1][2]))
      ];
    }
  }
  return ramp[ramp.length - 1][1];
}

function evaluatePixel(samples) {
  var bad = (samples.SCL == 3 || samples.SCL == 8 || samples.SCL == 9 || samples.SCL == 10 || samples.SCL == 11);
  if (bad || samples.dataMask === 0) {
    return [0, 0, 0, 0];
  }
  var ndvi = (samples.B08 - samples.B04) / (samples.B08 + samples.B04 + 1e-6);
  var rgb = rampColor(ndvi);
  return [rgb[0], rgb[1], rgb[2], 255];
}
"""

# Process API's default plan caps output images (2500x2500px) and
# billing scales with pixel count — capped well below that here since
# a farm parcel doesn't need more than this to look good in a Leaflet
# overlay, and it keeps requests fast.
_HEATMAP_MAX_DIM_PX = 1024


@retry(stop=stop_after_attempt(3), wait=wait_exponential(min=1, max=6))
async def get_ndvi_heatmap_png(geometry: dict, days_back: int = 30) -> dict:
    """
    Renders a colored NDVI PNG for the parcel via the Sentinel Hub
    Process API (image output) — distinct from get_ndvi()'s Statistics
    API call (single aggregate number only, no image). Powers the
    "carte NDVI" heatmap toggle on the map frontend.

    Returns dict with:
      - "image_base64": str | None — base64-encoded PNG bytes, ready
        for a `data:image/png;base64,...` URL / L.imageOverlay
      - "bounds": {"south", "west", "north", "east"} | None — WGS84
        bounding box of the geometry, for positioning the overlay
      - "warning": str | None
    """
    from shapely.geometry import shape

    poly = shape(geometry)
    minx, miny, maxx, maxy = poly.bounds  # (west, south, east, north)
    bounds = {"south": miny, "west": minx, "north": maxy, "east": maxx}

    if not settings.sentinel_hub_client_id or not settings.sentinel_hub_client_secret:
        return {
            "image_base64": None,
            "bounds": None,
            "warning": (
                "Sentinel Hub credentials not set. Create a free account at "
                "dataspace.copernicus.eu and an OAuth client, then set "
                "SENTINEL_HUB_CLIENT_ID / SENTINEL_HUB_CLIENT_SECRET in .env."
            ),
        }

    try:
        token = await _get_access_token()
    except httpx.HTTPError as e:
        return {"image_base64": None, "bounds": None, "warning": f"Copernicus auth failed: {e}"}

    end = datetime.now(timezone.utc)
    start = end - timedelta(days=days_back)

    width_px, height_px = _pixel_dims_for_resolution(geometry, target_resolution_m=10)
    width_px = max(32, min(width_px, _HEATMAP_MAX_DIM_PX))
    height_px = max(32, min(height_px, _HEATMAP_MAX_DIM_PX))

    payload = {
        "input": {
            "bounds": {
                "geometry": geometry,
                "properties": {"crs": "http://www.opengis.net/def/crs/OGC/1.3/CRS84"},
            },
            "data": [
                {
                    "type": "sentinel-2-l2a",
                    "dataFilter": {
                        "maxCloudCoverage": 60,
                        "mosaickingOrder": "leastCC",
                        "timeRange": {
                            "from": start.strftime("%Y-%m-%dT%H:%M:%SZ"),
                            "to": end.strftime("%Y-%m-%dT%H:%M:%SZ"),
                        },
                    },
                }
            ],
        },
        "output": {
            "width": width_px,
            "height": height_px,
            "responses": [{"identifier": "default", "format": {"type": "image/png"}}],
        },
        "evalscript": _NDVI_HEATMAP_EVALSCRIPT,
    }

    try:
        async with httpx.AsyncClient(timeout=30) as client:
            resp = await client.post(
                _PROCESS_URL,
                json=payload,
                headers={"Authorization": f"Bearer {token}"},
            )
            if resp.status_code >= 400:
                # Process API returns a JSON error body even though a
                # successful response is raw PNG bytes — surface the
                # real reason (auth scope, bad geometry, etc.) rather
                # than a bare status code.
                return {
                    "image_base64": None,
                    "bounds": None,
                    "warning": f"Sentinel Hub process request failed: {resp.status_code} — {resp.text[:1000]}",
                }
            png_bytes = resp.content
    except httpx.HTTPError as e:
        return {"image_base64": None, "bounds": None, "warning": f"Sentinel Hub process request failed: {e}"}

    if not png_bytes:
        return {"image_base64": None, "bounds": None, "warning": "Sentinel Hub returned an empty image."}

    return {
        "image_base64": base64.b64encode(png_bytes).decode("ascii"),
        "bounds": bounds,
        "warning": None,
    }


_L1C_TIMESERIES_URL = _STATISTICS_URL  # same Statistics API endpoint, different evalscript/data type

# Exact column order BreizhCrops' get_default_transform() selects for L1C
# input (see breizhcrops/datasets/breizhcrops.py) — the pretrained TempCNN
# was trained on columns in exactly this order, so getting this wrong
# silently feeds the model garbage rather than raising an error.
_BREIZHCROPS_L1C_BAND_ORDER = ["B01", "B10", "B11", "B12", "B02", "B03", "B04", "B05", "B06", "B07", "B08", "B8A", "B09"]

# Sentinel Hub band evalscript identifiers (zero-padded) in the same order.
_L1C_BANDS_EVALSCRIPT = """
//VERSION=3
function setup() {
  return {
    input: [{ bands: ["B01","B10","B11","B12","B02","B03","B04","B05","B06","B07","B08","B8A","B09","dataMask"] }],
    output: [
      { id: "data", bands: 13 },
      { id: "dataMask", bands: 1 }
    ]
  }
}
function evaluatePixel(samples) {
  return {
    data: [samples.B01, samples.B10, samples.B11, samples.B12, samples.B02, samples.B03,
           samples.B04, samples.B05, samples.B06, samples.B07, samples.B08, samples.B8A, samples.B09],
    dataMask: [samples.dataMask]
  }
}
"""


@retry(stop=stop_after_attempt(3), wait=wait_exponential(min=1, max=6))
async def get_band_timeseries(
    geometry: dict, days_back: int = 120, interval_days: int = 5
) -> dict:
    """
    Raw multi-band Sentinel-2 L1C time series for a parcel, as input to the
    Phase B DL crop classifier (BreizhCrops-pretrained TempCNN) — NOT NDVI,
    NOT fed into crop-suitability scoring, same "descriptive only" principle
    as get_ndvi().

    Uses L1C (not L2A like get_ndvi) because the pretrained model was
    trained on L1C's 13 raw bands. IMPORTANT: L1C has no Scene
    Classification Layer (SCL is an L2A-only atmospheric-correction
    product), so unlike get_ndvi() this can only filter clouds at the
    SCENE level (dataFilter.maxCloudCoverage / leastCC mosaicking), not
    per-pixel — a real, coarser trade-off versus the NDVI path, not an
    oversight.

    Returns dict with:
      - "bands": list[list[float]], shape [timesteps][13], columns in
        _BREIZHCROPS_L1C_BAND_ORDER order, values scaled to [0,1]
        reflectance (matching BreizhCrops' `x * 1e-4` scaling of raw
        digital numbers — Sentinel Hub's default S2L1C output is already
        DN/10000, so no extra scaling is applied here; VERIFY this
        assumption against a real response before trusting it, same
        "print raw JSON first" discipline as satellite_service.py's NDVI
        path)
      - "dates": list[str], one ISO date per timestep, same order as "bands"
      - "warning": str | None

    This is the RAW series — resampling/padding to the model's fixed
    45-timestep input is dl_service.py's job, done deterministically
    for reproducible inference rather than BreizhCrops' training-time random
    subsampling.
    """
    if not settings.sentinel_hub_client_id or not settings.sentinel_hub_client_secret:
        return {
            "bands": [], "dates": [],
            "warning": (
                "Sentinel Hub credentials not set. Create a free account at "
                "dataspace.copernicus.eu and an OAuth client, then set "
                "SENTINEL_HUB_CLIENT_ID / SENTINEL_HUB_CLIENT_SECRET in .env."
            ),
        }

    try:
        token = await _get_access_token()
    except httpx.HTTPError as e:
        return {"bands": [], "dates": [], "warning": f"Copernicus auth failed: {e}"}

    end = datetime.now(timezone.utc)
    start = end - timedelta(days=days_back)
    _ts_width_px, _ts_height_px = _pixel_dims_for_resolution(geometry, target_resolution_m=10)

    payload = {
        "input": {
            "bounds": {
                "geometry": geometry,
                "properties": {"crs": "http://www.opengis.net/def/crs/OGC/1.3/CRS84"},
            },
            "data": [
                {
                    "type": "sentinel-2-l1c",
                    "dataFilter": {"maxCloudCoverage": 60, "mosaickingOrder": "leastCC"},
                }
            ],
        },
        "aggregation": {
            "timeRange": {
                "from": start.strftime("%Y-%m-%dT%H:%M:%SZ"),
                "to": end.strftime("%Y-%m-%dT%H:%M:%SZ"),
            },
            "aggregationInterval": {"of": f"P{interval_days}D"},
            "evalscript": _L1C_BANDS_EVALSCRIPT,
            "width": _ts_width_px,
            "height": _ts_height_px,
        },
    }

    try:
        async with httpx.AsyncClient(timeout=60) as client:
            resp = await client.post(
                _L1C_TIMESERIES_URL,
                json=payload,
                headers={"Authorization": f"Bearer {token}", "Content-Type": "application/json"},
            )
            if resp.status_code >= 400:
                # httpx's generic HTTPError message ("Client error '400 Bad
                # Request'") discards the response body — Sentinel Hub always
                # fills it with the actual reason, so surface that instead of
                # guessing blind.
                return {
                    "bands": [], "dates": [],
                    "warning": f"Sentinel Hub statistics request failed: {resp.status_code} — {resp.text[:1000]}",
                }
            data = resp.json()
    except httpx.HTTPError as e:
        return {"bands": [], "dates": [], "warning": f"Sentinel Hub statistics request failed: {e}"}

    try:
        buckets = data.get("data", [])
        if not buckets:
            return {"bands": [], "dates": [], "warning": f"No Sentinel-2 L1C coverage found in the last {days_back} days for this parcel."}

        import math

        band_rows, dates = [], []
        for bucket in buckets:
            outputs = bucket.get("outputs", {}).get("data", {}).get("bands", {})
            if not outputs:
                continue  # empty bin (cloud-covered / no acquisition) — skip rather than insert a fabricated zero row
            # Statistics API names multi-band "data" output B0..B12 (index-based), in the evalscript's declared order
            row = []
            valid = True
            for i in range(13):
                stats = outputs.get(f"B{i}", {}).get("stats", {})
                mean = stats.get("mean")
                # Sentinel Hub can return the literal STRING "NaN" here (not
                # JSON null) for a bin where the aggregate computation broke
                # down — a real live response caught this. `mean is None`
                # alone doesn't catch it, and numpy's float32 array
                # construction silently coerces the string "NaN" into an
                # actual NaN float, poisoning the entire timestep without
                # erroring. Reject it explicitly here instead.
                is_bad = (
                    mean is None
                    or not isinstance(mean, (int, float))
                    or (isinstance(mean, float) and math.isnan(mean))
                    or stats.get("sampleCount", 0) == 0
                )
                if is_bad:
                    valid = False
                    break
                row.append(mean)
            if valid:
                band_rows.append(row)
                dates.append(bucket["interval"]["from"])

        if not band_rows:
            return {"bands": [], "dates": [], "warning": f"No cloud-free Sentinel-2 L1C bins found in the last {days_back} days for this parcel."}

        return {"bands": band_rows, "dates": dates, "warning": None}
    except (KeyError, IndexError, TypeError) as e:
        return {"bands": [], "dates": [], "warning": f"Unexpected Sentinel Hub response shape: {e}"}
