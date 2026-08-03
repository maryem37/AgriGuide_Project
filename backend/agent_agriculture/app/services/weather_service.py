"""
Open-Meteo, zero-auth, free, no key. Used for both current context and
(later) growing-season history for the tabular ML model.

Ported as-is from the standalone `agri-advisor-parcelle` prototype,
extended with a current/today snapshot for the frontend weather widget.
"""
import httpx
from tenacity import retry, stop_after_attempt, wait_exponential
from app.config import settings
from app.models.schemas import Coordinate, WeatherData


def _first(series: list | None):
    if not series:
        return None
    return series[0]


@retry(stop=stop_after_attempt(3), wait=wait_exponential(min=1, max=6))
async def get_weather_data(centroid: Coordinate, days: int = 16) -> WeatherData:
    params = {
        "latitude": centroid.lat,
        "longitude": centroid.lon,
        "current": "temperature_2m,relative_humidity_2m,precipitation,weather_code,wind_speed_10m",
        "daily": (
            "temperature_2m_mean,temperature_2m_max,temperature_2m_min,"
            "precipitation_sum,sunrise,sunset,et0_fao_evapotranspiration,weather_code"
        ),
        "forecast_days": min(days, 16),
        "timezone": "auto",
        "wind_speed_unit": "kmh",
    }
    try:
        async with httpx.AsyncClient(timeout=10) as client:
            resp = await client.get(settings.open_meteo_base, params=params)
            resp.raise_for_status()
            data = resp.json()
        daily = data.get("daily", {})
        current = data.get("current", {}) or {}
        temps = daily.get("temperature_2m_mean")
        precip = daily.get("precipitation_sum")

        warning = None
        # Open-Meteo sometimes returns null for the trailing day(s) of a
        # 16-day forecast (that day's model run isn't complete yet).
        # Keep the raw list (with Nones) for transparency, but flag it
        # so callers know to filter before doing arithmetic on it.
        if temps and any(t is None for t in temps):
            warning = "Some trailing forecast days had no data yet (Open-Meteo forecast edge); filtered for scoring."

        weather_code = current.get("weather_code")
        if weather_code is None:
            weather_code = _first(daily.get("weather_code"))

        return WeatherData(
            source="open-meteo",
            daily_temp_mean_c=temps,
            daily_precip_mm=precip,
            daily_et0_mm=daily.get("et0_fao_evapotranspiration"),
            daily_dates=daily.get("time"),
            current_temp_c=current.get("temperature_2m"),
            current_humidity_pct=current.get("relative_humidity_2m"),
            current_wind_kmh=current.get("wind_speed_10m"),
            current_precip_mm=current.get("precipitation"),
            weather_code=weather_code,
            sunrise=_first(daily.get("sunrise")),
            sunset=_first(daily.get("sunset")),
            today_temp_min_c=_first(daily.get("temperature_2m_min")),
            today_temp_max_c=_first(daily.get("temperature_2m_max")),
            observed_at=current.get("time"),
            warning=warning,
        )
    except httpx.HTTPError as e:
        return WeatherData(source="unavailable", warning=f"Open-Meteo request failed: {e}")
