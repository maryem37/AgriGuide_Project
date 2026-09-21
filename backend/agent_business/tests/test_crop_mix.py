"""Tests unitaires du service d'optimisation d'asassolement (Crop Mix Optimization)."""

import pytest
from app.models.schemas import CropRecommendation, CropMixRequest, CropMixResponse
from app.services.crop_mix_service import optimize_crop_mix


@pytest.fixture
def sample_crop_recommendations():
    return [
        CropRecommendation(
            rang=1,
            culture="ble_tendre",
            score_compatibilite=85.0,
            cycle_jours=240,
            besoins_irrigation={"niveau": "faible"},
            besoins_engrais={"n": 160},
            besoins_pesticides={"traitements": 2},
            feature_importance={"ph": 0.3},
        ),
        CropRecommendation(
            rang=2,
            culture="mais",
            score_compatibilite=80.0,
            cycle_jours=150,
            besoins_irrigation={"niveau": "eleve"},
            besoins_engrais={"n": 220},
            besoins_pesticides={"traitements": 3},
            feature_importance={"temp": 0.4},
        ),
        CropRecommendation(
            rang=3,
            culture="colza",
            score_compatibilite=75.0,
            cycle_jours=270,
            besoins_irrigation={"niveau": "moyen"},
            besoins_engrais={"n": 180},
            besoins_pesticides={"traitements": 2},
            feature_importance={"ph": 0.2},
        ),
        CropRecommendation(
            rang=4,
            culture="tournesol",
            score_compatibilite=30.0,  # Below default min_compatibility_score threshold (40.0)
            cycle_jours=130,
            besoins_irrigation={"niveau": "faible"},
            besoins_engrais={"n": 100},
            besoins_pesticides={"traitements": 1},
            feature_importance={"temp": 0.2},
        ),
    ]


def test_optimize_crop_mix_basic(sample_crop_recommendations):
    req = CropMixRequest(
        terrain_id="TERRAIN-TEST-100",
        superficie_disponible_ha=100.0,
        budget_input=120000.0,
        crop_recommendations=sample_crop_recommendations,
        max_single_crop_share=0.50,
        min_compatibility_score=40.0,
    )
    res = optimize_crop_mix(req)

    assert isinstance(res, CropMixResponse)
    assert res.terrain_id == "TERRAIN-TEST-100"
    assert res.superficie_totale_ha == 100.0
    assert res.superficie_utilisee_ha <= 100.0
    assert res.budget_utilise_eur <= 120000.0
    assert res.optimization_status == "OPTIMAL"

    # Verify monoculture cap constraint: no single crop exceeds 50% (50.0 ha)
    for alloc in res.allocations:
        assert alloc.hectares_alloues <= 50.01

    # Verify low-compatibility crop ("tournesol", score 30) was filtered out
    allocated_cultures = [a.culture for a in res.allocations]
    assert "tournesol" not in allocated_cultures

    # Verify HHI score is computed
    assert 0 <= res.diversification_hhi_score <= 10000
    assert res.diversification_label in ["DIVERSIFIÉ", "MODÉRÉ", "CONCENTRÉ"]


def test_optimize_crop_mix_tight_budget(sample_crop_recommendations):
    # Tight budget: €20,000 for 100 ha
    req = CropMixRequest(
        terrain_id="TERRAIN-TIGHT-BUDGET",
        superficie_disponible_ha=100.0,
        budget_input=20000.0,
        crop_recommendations=sample_crop_recommendations,
    )
    res = optimize_crop_mix(req)

    assert res.budget_utilise_eur <= 20000.0
    assert res.superficie_utilisee_ha < 100.0  # Land unused due to budget limit
