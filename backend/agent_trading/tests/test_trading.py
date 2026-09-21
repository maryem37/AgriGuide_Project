import pytest
from fastapi.testclient import TestClient
from app.main import app

client = TestClient(app)

def test_read_root():
    response = client.get("/")
    assert response.status_code == 200
    data = response.json()
    assert data["agent"] == "agent_trading"

def test_get_tickers():
    response = client.get("/trading/tickers")
    assert response.status_code == 200
    data = response.json()
    assert isinstance(data, list)
    assert len(data) >= 1

def test_evaluate_strategy():
    payload = {
        "commodity_symbol": "EBM",
        "total_harvest_tons": 500,
        "already_committed_tons": 150,
        "break_even_cost_eur_ton": 180,
        "storage_capacity_tons": 200,
        "target_margin_pct": 20
    }
    response = client.post("/trading/strategy", json=payload)
    assert response.status_code == 200
    data = response.json()
    assert data["action"] in ["SELL", "HOLD", "STORE", "HEDGE"]
    assert data["confidence_score_pct"] > 0
    assert len(data["step_by_step_plan"]) >= 1
