from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.routers.monitoring import router as monitoring_router

app = FastAPI(
    title="AgriAdvisor — Agent Monitoring",
    description="Briefing quotidien météo, irrigation et alertes (LangGraph + Mistral).",
    version="1.0.0",
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(monitoring_router)


@app.get("/health")
def health():
    return {"status": "ok", "agent": "monitoring"}
