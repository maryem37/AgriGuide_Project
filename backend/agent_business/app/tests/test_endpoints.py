"""
Test des endpoints FastAPI via TestClient (pas besoin de lancer un serveur).
Exécution : python -m app.tests.test_endpoints (depuis backend/agent_business/)
"""

from fastapi.testclient import TestClient

from app.main import app
from app.data.mock_crop_recommendations import (
    get_mock_crop_recommendations,
    MOCK_TERRAIN_ID,
    MOCK_TERRAIN_SUPERFICIE_HA,
    MOCK_DATE_PLANTATION,
)

client = TestClient(app)


def test_health():
    r = client.get("/health")
    assert r.status_code == 200
    assert r.json()["status"] == "ok"
    print("[OK] /health")


def test_scenarios_endpoint():
    payload = {
        "terrain_id": MOCK_TERRAIN_ID,
        "superficie_disponible_ha": MOCK_TERRAIN_SUPERFICIE_HA,
        "budget_input": 25000.0,
        "date_plantation_prevue": MOCK_DATE_PLANTATION.isoformat(),
        "crop_recommendations": get_mock_crop_recommendations(),
        "nb_scenarios": 3,
    }
    r = client.post("/business/scenarios", json=payload)
    assert r.status_code == 200, r.text
    data = r.json()
    assert len(data["scenarios"]) == 3
    assert all(0 <= s["matching_score"] <= 100 for s in data["scenarios"])
    print(f"[OK] /business/scenarios -> {[s['culture'] for s in data['scenarios']]}")
    return data


def test_decision_endpoint(scenarios_data):
    scenarios = scenarios_data["scenarios"]
    culture_1, culture_2 = scenarios[0]["culture"], scenarios[1]["culture"]

    payload = {
        "terrain_id": MOCK_TERRAIN_ID,
        "superficie_disponible_ha": MOCK_TERRAIN_SUPERFICIE_HA,
        "allocations": [
            {"scenario_id": "s1", "culture": culture_1, "hectares_alloues": 3.0},
            {"scenario_id": "s2", "culture": culture_2, "hectares_alloues": 3.0},
        ],
    }
    r = client.post("/business/decision", json=payload)
    assert r.status_code == 200, r.text
    data = r.json()
    assert data["statut"] == "confirmed"
    assert data["superficie_totale_allouee_ha"] == 6.0
    print(f"[OK] /business/decision -> coût final {data['cout_final']} EUR")


def test_decision_rejects_over_allocation():
    payload = {
        "terrain_id": MOCK_TERRAIN_ID,
        "superficie_disponible_ha": MOCK_TERRAIN_SUPERFICIE_HA,
        "allocations": [
            {"scenario_id": "s1", "culture": "tomate", "hectares_alloues": 999.0},
        ],
    }
    r = client.post("/business/decision", json=payload)
    assert r.status_code == 400
    print("[OK] /business/decision rejette une sur-allocation (400)")


if __name__ == "__main__":
    test_health()
    scenarios_data = test_scenarios_endpoint()
    test_decision_endpoint(scenarios_data)
    test_decision_rejects_over_allocation()
    print("\nTous les tests sont passés.")
