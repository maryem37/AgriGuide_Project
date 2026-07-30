"""
Section 5 — Open-Meteo, zero-auth, free, no key. Used for both current
context and (later) growing-season history for the tabular ML model.
"""
import httpx
from tenacity import retry, stop_after_attempt, wait_exponential
from config import settings
from schemas import Coordinate, WeatherData


@retry(stop=stop_after_attempt(3), wait=wait_exponential(min=1, max=6))
async def get_weather_data(centroid: Coordinate, days: int = 16) -> WeatherData:
    params = {
        "latitude": centroid.lat,
        "longitude": centroid.lon,
        "daily": "temperature_2m_mean,precipitation_sum",
        "forecast_days": min(days, 16),
        "timezone": "auto",
    }
    try:
        async with httpx.AsyncClient(timeout=10) as client:
            resp = await client.get(settings.open_meteo_base, params=params)
            resp.raise_for_status()
            data = resp.json()
        daily = data.get("daily", {})
        temps = daily.get("temperature_2m_mean")
        precip = daily.get("precipitation_sum")

        warning = None
        # Open-Meteo sometimes returns null for the trailing day(s) of a
        # 16-day forecast (that day's model run isn't complete yet).
        # Keep the raw list (with Nones) for transparency, but flag it
        # so callers know to filter before doing arithmetic on it.
        if temps and any(t is None for t in temps):
            warning = "Some trailing forecast days had no data yet (Open-Meteo forecast edge); filtered for scoring."

        return WeatherData(
            source="open-meteo",
            daily_temp_mean_c=temps,
            daily_precip_mm=precip,
            daily_dates=daily.get("time"),
            warning=warning,
        )
    except httpx.HTTPError as e:
        return WeatherData(source="unavailable", warning=f"Open-Meteo request failed: {e}")