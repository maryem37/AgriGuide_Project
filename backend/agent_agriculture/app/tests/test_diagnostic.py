import pytest
from fastapi.testclient import TestClient
from app.main import app

client = TestClient(app)

def test_get_diagnostic_samples():
    response = client.get("/agriculture/diagnostic/samples")
    assert response.status_code == 200
    data = response.json()
    assert isinstance(data, list)
    assert len(data) >= 3
    assert data[0]["species"] == "Rouille brune du blé"
    assert len(data[0]["recommendations"]) >= 4

def test_scan_with_sample_id():
    response = client.post(
        "/agriculture/diagnostic/scan",
        data={"sample_id": "sample_rouille_ble", "crop_context": "Blé Tendre"}
    )
    assert response.status_code == 200
    data = response.json()
    assert data["species"] == "Rouille brune du blé"
    assert data["scientific_name"] == "Puccinia triticina"
    assert data["risk_level"] == "critical"
    assert len(data["recommendations"]) >= 4

def test_scan_with_file_fallback():
    response = client.post(
        "/agriculture/diagnostic/scan",
        files={"image": ("test_leaf.jpg", b"fake_image_bytes", "image/jpeg")},
        data={"crop_context": "Blé Tendre"}
    )
    assert response.status_code == 200
    data = response.json()
    assert "Rouille" in data["species"] or "Symptôme" in data["species"]
    assert len(data["recommendations"]) >= 4
