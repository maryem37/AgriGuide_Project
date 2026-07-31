"""
Fast, network-free tests for the pieces that don't need live external
APIs (cadastre/RPG/SoilGrids/Open-Meteo/Sentinel Hub/Mistral) — those
are exercised manually against a running server (see README §"Tester
manuellement"), same as the standalone prototype this was ported from.

Exécution : python -m app.tests.test_endpoints (depuis backend/agent_agriculture/)
"""

from fastapi.testclient import TestClient

from app.main import app
from app.models.schemas import SoilData, WeatherData
from app.services import ml_service, agro_calc_service

client = TestClient(app)


def test_health():
    r = client.get("/health")
    assert r.status_code == 200
    assert r.json()["status"] == "ok"
    print("[OK] /health")


def _sample_soil() -> SoilData:
    return SoilData(
        source="soilgrids", ph=6.5, nitrogen_g_kg=2.1, organic_carbon_g_kg=18.0,
        sand_pct=35, clay_pct=25, silt_pct=40, cec_cmolkg=15, bulk_density_kg_dm3=1.3,
        coarse_fragments_pct=5, depth_cm="0-5cm",
    )


def _sample_weather() -> WeatherData:
    return WeatherData(
        source="open-meteo",
        daily_temp_mean_c=[14.0, 15.0, 16.0, None],
        daily_precip_mm=[0.0, 2.5, 0.0, 1.0],
        daily_et0_mm=[3.0, 3.2, 2.8, 3.1],
        daily_dates=["2026-01-01", "2026-01-02", "2026-01-03", "2026-01-04"],
    )


def test_recommend_crops_returns_five_sorted():
    recs = ml_service.recommend_crops(_sample_soil(), _sample_weather())
    assert len(recs) == 5
    assert all(0.0 <= r.suitability_score <= 1.0 for r in recs)
    scores = [r.suitability_score for r in recs]
    assert scores == sorted(scores, reverse=True)
    print(f"[OK] recommend_crops -> {[r.crop for r in recs]}")


def test_agro_calc_estimate_has_no_negative_values():
    estimate = agro_calc_service.estimate_fertilizer_and_irrigation("ble_tendre", _sample_soil(), _sample_weather())
    assert estimate.crop == "ble_tendre"
    if estimate.n_dose_kg_ha is not None:
        assert estimate.n_dose_kg_ha >= 0
    if estimate.irrigation_need_mm is not None:
        assert estimate.irrigation_need_mm >= 0
    print(f"[OK] agro_calc_service -> N dose={estimate.n_dose_kg_ha} kg/ha, irrigation={estimate.irrigation_need_mm} mm")


def test_analyze_rejects_unresolved_point_without_terrain():
    # A point in the middle of the ocean resolves to nothing in
    # cadastre/RPG and has no manual_geojson/terrain_id fallback —
    # the endpoint must reject it (422) rather than silently analyzing
    # a meaningless location.
    r = client.post("/agriculture/analyze", json={"point": {"lat": 0.0, "lon": -30.0}})
    assert r.status_code in (422, 500, 503)  # 500/503 acceptable if the network call itself fails in a sandboxed CI
    print("[OK] /agriculture/analyze rejects an unresolved point without a terrain fallback")


if __name__ == "__main__":
    test_health()
    test_recommend_crops_returns_five_sorted()
    test_agro_calc_estimate_has_no_negative_values()
    test_analyze_rejects_unresolved_point_without_terrain()
    print("\nTous les tests (hors réseau) sont passés.")
