"""
AgriGuide HTTP adapter for the Agricultural Waste Intelligence knowledge base.

Run from backend/waste_agents:
    uvicorn api.main:app --reload --port 8004

This service is read-only against canonical_knowledge.json (no LLM / search
keys required). Live research remains available via the Streamlit UI.
"""
from __future__ import annotations

import sys
from pathlib import Path

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

# Allow `from models import …` / `from services…` like the Streamlit app.
PROJECT_ROOT = Path(__file__).resolve().parent.parent
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from api.router import router as waste_router  # noqa: E402
from api.service import _load_kb  # noqa: E402

app = FastAPI(
    title="AgriGuide — Agent Déchets / Valorisation",
    description=(
        "Expose la base de connaissances waste_agents au parcours Agriculture → "
        "Business → Marketplace."
    ),
    version="1.0.0",
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(waste_router)


@app.on_event("startup")
def _warm_kb() -> None:
    try:
        kb = _load_kb()
        print(f"[waste_api] Knowledge base loaded: {len(kb.crops)} crops")
    except Exception as exc:  # noqa: BLE001
        print(f"[waste_api] Failed to warm knowledge base: {exc}")


@app.get("/health")
def health():
    try:
        kb = _load_kb()
        stats = kb.stats()
        return {"status": "ok", "agent": "waste", **stats}
    except Exception as exc:  # noqa: BLE001
        return {"status": "degraded", "agent": "waste", "error": str(exc)}
