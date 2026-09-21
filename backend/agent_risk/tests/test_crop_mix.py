"""Tests unitaires du service d'optimisation d'asassolement de l'agent_risk (Port 8010)."""

import pytest
from app.models.schemas import CropRecommendationInput, CropMixRequest, CropMixResponse
from app.services.crop_mix_service import optimize_crop_mix


@pytest.fixture
def sample_crop_recommendations():
    return [
        CropRecommendationInput(
            rang=1,
            culture="ble_tendre",
            score_compatibilite=85.0,
            cycle_jours=240,
        ),
        CropRecommendationInput(
            rang=2,
            culture="mais",
            score_compatibilite=80.0,
            cycle_jours=150,
        ),
        CropRecommendationInput(
            rang=3,
            culture="colza",
            score_compatibilite=75.0,
            cycle_jours=270,
        ),
    ]


def test_optimize_crop_mix_basic(sample_crop_recommendations):
    req = CropMixRequest(
        terrain_id="TERRAIN-RISK-100",
        superficie_disponible_ha=100.0,
        budget_input=120000.0,
        crop_recommendations=sample_crop_recommendations,
        max_single_crop_share=0.50,
        min_compatibility_score=40.0,
    )
    res = optimize_crop_mix(req)

    assert isinstance(res, CropMixResponse)
    assert res.terrain_id == "TERRAIN-RISK-100"
    assert res.superficie_totale_ha == 100.0
    assert res.superficie_utilisee_ha <= 100.0
    assert res.budget_utilise_eur <= 120000.0
    assert res.optimization_status == "OPTIMAL"
    assert 0 <= res.diversification_hhi_score <= 10000
