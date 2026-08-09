"""
Test des endpoints FastAPI via TestClient (pas besoin de lancer un serveur).
Exécution : python -m app.tests.test_endpoints (depuis backend/agent_business/)
"""

import os
from datetime import date

import pytest
from fastapi.testclient import TestClient

os.environ["BUSINESS_PERSISTENCE_MODE"] = "memory"
os.environ["BUSINESS_AUTH_DISABLED"] = "1"

from app.main import app  # noqa: E402
from app.services.scoring import CandidatScoring, calculer_matching_scores  # noqa: E402

client = TestClient(app)
TERRAIN_ID = "11111111-1111-1111-1111-111111111111"
SUPERFICIE_HA = 12.0


def recommendations():
    def crop(name, rank, compatibility, irrigation, nitrogen):
        return {
            "rang": rank,
            "culture": name,
            "score_compatibilite": compatibility,
            "cycle_jours": 120,
            "besoins_irrigation": {"irrigation_need_mm": irrigation},
            "besoins_engrais": {"n_dose_kg_ha": nitrogen},
            "besoins_pesticides": {"traitements_par_saison": 2},
            "feature_importance": {},
        }

    return [
        crop("ble", 1, 92, 80, 160),
        crop("mais", 2, 84, 160, 190),
        crop("tournesol", 3, 76, 40, 60),
        crop("orge", 4, 72, 60, 120),
    ]


@pytest.fixture
def scenarios_data():
    payload = {
        "terrain_id": TERRAIN_ID,
        "superficie_disponible_ha": SUPERFICIE_HA,
        "budget_input": 25000.0,
        "date_plantation_prevue": date(2026, 3, 15).isoformat(),
        "crop_recommendations": recommendations(),
        "nb_scenarios": 3,
    }
    response = client.post("/business/scenarios", json=payload)
    assert response.status_code == 200, response.text
    return response.json()


def test_health():
    r = client.get("/health")
    assert r.status_code == 200
    assert r.json()["status"] == "ok"
    print("[OK] /health")


def test_business_endpoints_require_auth(monkeypatch):
    monkeypatch.delenv("BUSINESS_AUTH_DISABLED", raising=False)
    response = client.post("/business/scenarios", json={})
    assert response.status_code == 401


def test_scenarios_endpoint(scenarios_data):
    assert len(scenarios_data["scenarios"]) == 3
    for scenario in scenarios_data["scenarios"]:
        assert scenario["id"]
        assert 0 <= scenario["matching_score"] <= 100
        assert scenario["score_compatibilite"] > 0
        assert "roi_pct" in scenario["indicateurs_financiers"]
        assert "profit_margin_pct" in scenario["indicateurs_financiers"]
        assert scenario["confiance_donnees"]["raisons"]


def test_decision_endpoint(scenarios_data):
    scenarios = scenarios_data["scenarios"]
    culture_1, culture_2 = scenarios[0]["culture"], scenarios[1]["culture"]

    payload = {
        "terrain_id": TERRAIN_ID,
        "superficie_disponible_ha": SUPERFICIE_HA,
        "allocations": [
            {"scenario_id": scenarios[0]["id"], "culture": culture_1, "hectares_alloues": 1.0},
            {"scenario_id": scenarios[1]["id"], "culture": culture_2, "hectares_alloues": 1.0},
        ],
    }
    r = client.post("/business/decision", json=payload)
    assert r.status_code == 200, r.text
    data = r.json()
    assert data["statut"] == "confirmed"
    assert data["superficie_totale_allouee_ha"] == 2.0
    assert all(a["date_maturite_prevue"] for a in data["allocations"])
    latest = client.get(f"/business/decisions/{TERRAIN_ID}/latest")
    assert latest.status_code == 200
    assert latest.json()["decision_id"] == data["decision_id"]


def test_decision_rejects_over_allocation(scenarios_data):
    scenario = scenarios_data["scenarios"][0]
    payload = {
        "terrain_id": TERRAIN_ID,
        "superficie_disponible_ha": SUPERFICIE_HA,
        "allocations": [
            {
                "scenario_id": scenario["id"],
                "culture": scenario["culture"],
                "hectares_alloues": 999.0,
            },
        ],
    }
    r = client.post("/business/decision", json=payload)
    assert r.status_code == 400
    print("[OK] /business/decision rejette une sur-allocation (400)")


def test_empty_recommendations_rejected():
    payload = {
        "terrain_id": TERRAIN_ID,
        "superficie_disponible_ha": SUPERFICIE_HA,
        "budget_input": 25000,
        "date_plantation_prevue": "2026-03-15",
        "crop_recommendations": [],
    }
    assert client.post("/business/scenarios", json=payload).status_code == 422


def test_agriculture_compatibility_influences_score():
    candidates = [
        CandidatScoring("compatible", 1000, 0.2, 10, 0.95),
        CandidatScoring("incompatible", 1000, 0.2, 10, 0.20),
    ]
    scores = calculer_matching_scores(candidates, superficie_disponible_ha=10)
    assert scores["compatible"] > scores["incompatible"]
