"""Tests unitaires du service de risque climatique paramétrique et d'assurance récolte."""

import pytest
from app.models.schemas import ClimateRiskRequest, ClimateRiskResponse
from app.services.climate_risk_service import (
    calculate_climate_risk,
    compute_ndvi_decay,
    compute_spei,
    compute_spi,
)


def test_compute_spi_normal():
    # Série standard de précipitation mensuelle (12 mois)
    precip = [60.0, 55.0, 50.0, 45.0, 40.0, 30.0, 20.0, 25.0, 35.0, 50.0, 65.0, 70.0]
    spi = compute_spi(precip)
    assert isinstance(spi, float)
    assert -3.0 <= spi <= 3.0


def test_compute_spi_zero_precipitation_q0_100():
    # Cas limite : Sécheresse extrême q0 = 100% (aucune précipitation)
    precip = [0.0] * 12
    spi = compute_spi(precip)
    assert spi == -2.5  # Doit retourner -2.5 sans planter ni retourner NaN


def test_compute_spei_normal():
    # Bilan hydrique D = P - ETP
    water_balance = [40.0, 30.0, 5.0, -25.0, -50.0, -90.0, -110.0, -83.0, -25.0, 23.0, 50.0, 55.0]
    spei = compute_spei(water_balance)
    assert isinstance(spei, float)
    assert -3.0 <= spei <= 3.0


def test_compute_ndvi_decay_degraded_mode():
    # Degraded mode when Sentinel-2 NDVI is unavailable (None)
    decay_none = compute_ndvi_decay(None, 0.85)
    assert decay_none == 0.0

    # Normal mode with valid NDVI
    decay_valid = compute_ndvi_decay(0.68, 0.85)
    assert round(decay_valid, 2) == 0.20


def test_calculate_climate_risk_response():
    req = ClimateRiskRequest(
        lat=48.85,
        lon=2.35,
        crop_type="ble_tendre",
        parcel_id="PARCEL-TEST-1",
        ndvi_current=0.72,
        ndvi_max_baseline=0.85,
    )
    response = calculate_climate_risk(req)
    
    assert isinstance(response, ClimateRiskResponse)
    assert response.parcel_id == "PARCEL-TEST-1"
    assert response.crop_type == "ble_tendre"
    assert 0 <= response.risk_score <= 100
    assert response.risk_level in ["FAIBLE", "MODÉRÉ", "ÉLEVÉ", "CRITIQUE"]
    assert response.insurance_recommendation.estimated_annual_premium_eur_ha > 0
    assert "Note V1" in response.methodology_note
