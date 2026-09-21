"""FastAPI Main App for Risk Analyst Agent (Port 8010)."""

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from app.routers import risk

app = FastAPI(
    title="AgriGuide — Risk Analyst Agent",
    description="Microservice d'évaluation centralisée des risques agricoles (Port 8010)",
    version="1.0.0",
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(risk.router)


@app.get("/health")
def health_check():
    return {
        "status": "ok",
        "service": "agent_risk",
        "port": 8010,
        "models": ["Belhsen et al. (2026) Parametric Climate Risk", "Linprog Crop Mix HHI"],
    }
