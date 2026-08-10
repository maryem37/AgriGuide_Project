import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from fastapi.testclient import TestClient
from main import app
from middleware.auth import get_current_user_id

PNG_BYTES = (
    b"\x89PNG\r\n\x1a\n\x00\x00\x00\rIHDR\x00\x00\x00\x01\x00\x00\x00\x01\x08\x06"
    b"\x00\x00\x00\x1f\x15\xc4\x89\x00\x00\x00\nIDATx\x9cc```\x00\x00\x00\x02\x00\x01"
    b"\xe2'\xbc\x33\x00\x00\x00\x00IEND\xaeB`\x82"
)

def fake_user():
    return "test-user"

def main():
    app.dependency_overrides[get_current_user_id] = fake_user
    client = TestClient(app)
    files = {"image": ("test.png", PNG_BYTES, "image/png")}
    data = {"region": "Occitanie"}
    resp = client.post("/api/detect", files=files, data=data)
    print("Status:", resp.status_code)
    try:
        print(resp.json())
    except Exception:
        print(resp.text)

if __name__ == "__main__":
    main()
