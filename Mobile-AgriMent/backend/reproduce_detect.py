import sys
from pathlib import Path

# Ensure repo root is on sys.path
sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

import jwt
import json
import requests
from config.settings import get_settings

settings = get_settings()

def make_token(sub="00000000-0000-0000-0000-000000000000"):
    payload = {"sub": sub}
    token = jwt.encode(payload, settings.JWT_SECRET, algorithm=settings.JWT_ALGORITHM)
    return token

# 1x1 transparent PNG
PNG_BYTES = (
    b"\x89PNG\r\n\x1a\n\x00\x00\x00\rIHDR\x00\x00\x00\x01\x00\x00\x00\x01\x08\x06"
    b"\x00\x00\x00\x1f\x15\xc4\x89\x00\x00\x00\nIDATx\x9cc```\x00\x00\x00\x02\x00\x01"
    b"\xe2'\xbc\x33\x00\x00\x00\x00IEND\xaeB`\x82"
)

def main():
    token = make_token()
    # verify token locally
    try:
        decoded = jwt.decode(token, settings.JWT_SECRET, algorithms=[settings.JWT_ALGORITHM])
        print("Local token decoded:", decoded)
    except Exception as e:
        print("Local token decode failed:", e)
    
    url = "http://127.0.0.1:8080/api/detect"
    headers = {"Authorization": f"Bearer {token}"}
    files = {"image": ("test.png", PNG_BYTES, "image/png")}
    data = {"region": "Occitanie"}
    try:
        resp = requests.post(url, headers=headers, files=files, data=data, timeout=30)
    except Exception as e:
        print("Request failed:", e)
        return
    print("Status:", resp.status_code)
    try:
        print(json.dumps(resp.json(), indent=2))
    except Exception:
        print(resp.text)

if __name__ == "__main__":
    main()
