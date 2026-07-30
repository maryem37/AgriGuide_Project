"""
Tests des endpoints FastAPI via TestClient — nécessite une vraie base
PostgreSQL démarrée avec `database/schema.sql` (voir README.md du module).

Exécution : python -m app.tests.test_endpoints (depuis backend/auth/)
"""

import uuid

from fastapi.testclient import TestClient

from app.main import app

client = TestClient(app)


def _unique_email(prefix: str) -> str:
    return f"{prefix}-{uuid.uuid4().hex[:8]}@example.com"


def test_health():
    r = client.get("/health")
    assert r.status_code == 200
    assert r.json()["status"] == "ok"
    print("[OK] /health")


def test_signup_acheteur():
    payload = {
        "email": _unique_email("acheteur"),
        "password": "motdepasse123",
        "nom": "Alice Acheteur",
        "role": "acheteur",
    }
    r = client.post("/auth/signup", json=payload)
    assert r.status_code == 201, r.text
    data = r.json()
    assert data["user"]["role"] == "acheteur"
    assert data["user"]["equipements"] == []
    assert data["user"]["terrains"] == []
    print("[OK] /auth/signup (acheteur)")
    return data


def test_signup_farmer_requires_terrain():
    payload = {
        "email": _unique_email("farmer-invalide"),
        "password": "motdepasse123",
        "nom": "Jean Sans Terre",
        "role": "farmer",
        "equipements": ["tracteur"],
        "terrains": [],
    }
    r = client.post("/auth/signup", json=payload)
    assert r.status_code == 422, r.text
    print("[OK] /auth/signup rejette un farmer sans terrain (422)")


def test_signup_farmer():
    payload = {
        "email": _unique_email("farmer"),
        "password": "motdepasse123",
        "nom": "Jean Farmer",
        "telephone": "0600000000",
        "role": "farmer",
        "equipements": ["tracteur", "pulverisateur"],
        "terrains": [
            {
                "nom": "Parcelle Nord",
                "points": [[48.85, 2.35], [48.86, 2.35], [48.86, 2.36], [48.85, 2.36]],
            }
        ],
    }
    r = client.post("/auth/signup", json=payload)
    assert r.status_code == 201, r.text
    data = r.json()
    assert data["user"]["role"] == "farmer"
    assert set(data["user"]["equipements"]) == {"tracteur", "pulverisateur"}
    assert len(data["user"]["terrains"]) == 1
    assert data["user"]["terrains"][0]["nom"] == "Parcelle Nord"
    assert data["user"]["terrains"][0]["superficie_ha"] > 0
    print(f"[OK] /auth/signup (farmer) -> superficie calculée = {data['user']['terrains'][0]['superficie_ha']} ha")
    return data


def test_signup_duplicate_email_rejected(existing_email: str):
    payload = {
        "email": existing_email,
        "password": "motdepasse123",
        "nom": "Doublon",
        "role": "acheteur",
    }
    r = client.post("/auth/signup", json=payload)
    assert r.status_code == 409
    print("[OK] /auth/signup rejette un email déjà utilisé (409)")


def test_signin_and_me(email: str, password: str):
    r = client.post("/auth/signin", json={"email": email, "password": password})
    assert r.status_code == 200, r.text
    token = r.json()["access_token"]
    print("[OK] /auth/signin")

    r = client.get("/auth/me", headers={"Authorization": f"Bearer {token}"})
    assert r.status_code == 200, r.text
    print("[OK] /auth/me")
    return token


def test_signin_wrong_password_rejected(email: str):
    r = client.post("/auth/signin", json={"email": email, "password": "mauvais-mot-de-passe"})
    assert r.status_code == 401
    print("[OK] /auth/signin rejette un mauvais mot de passe (401)")


def test_update_equipements(token: str):
    r = client.put(
        "/auth/me/equipements",
        json={"equipements": ["moissonneuse_batteuse"]},
        headers={"Authorization": f"Bearer {token}"},
    )
    assert r.status_code == 200, r.text
    assert r.json()["equipements"] == ["moissonneuse_batteuse"]
    print("[OK] PUT /auth/me/equipements")


def test_terrain_crud(token: str):
    headers = {"Authorization": f"Bearer {token}"}

    r = client.post(
        "/auth/me/terrains",
        json={"nom": "Parcelle Sud", "points": [[48.80, 2.30], [48.81, 2.30], [48.81, 2.31]]},
        headers=headers,
    )
    assert r.status_code == 201, r.text
    terrain_id = r.json()["id"]
    print("[OK] POST /auth/me/terrains")

    r = client.put(
        f"/auth/me/terrains/{terrain_id}",
        json={"nom": "Parcelle Sud (renommée)"},
        headers=headers,
    )
    assert r.status_code == 200, r.text
    assert r.json()["nom"] == "Parcelle Sud (renommée)"
    print("[OK] PUT /auth/me/terrains/{id}")

    r = client.delete(f"/auth/me/terrains/{terrain_id}", headers=headers)
    assert r.status_code == 204, r.text
    print("[OK] DELETE /auth/me/terrains/{id}")


def test_unauthenticated_me_rejected():
    r = client.get("/auth/me")
    assert r.status_code == 401
    print("[OK] GET /auth/me sans token rejeté (401)")


if __name__ == "__main__":
    test_health()
    acheteur_data = test_signup_acheteur()
    test_signup_farmer_requires_terrain()
    farmer_data = test_signup_farmer()
    test_signup_duplicate_email_rejected(farmer_data["user"]["email"])
    farmer_email = farmer_data["user"]["email"]
    token = test_signin_and_me(farmer_email, "motdepasse123")
    test_signin_wrong_password_rejected(farmer_email)
    test_update_equipements(token)
    test_terrain_crud(token)
    test_unauthenticated_me_rejected()
    print("\nTous les tests sont passés.")
