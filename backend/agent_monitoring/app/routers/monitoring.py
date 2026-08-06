from fastapi import APIRouter, HTTPException

from app.agent.graph import run_analysis
from app.config import settings
from app.models.schemas import AnalyzeRequest, AnalyzeResponse

router = APIRouter(prefix="/monitoring", tags=["monitoring"])


@router.post("/analyze", response_model=AnalyzeResponse)
def analyze_farm(request: AnalyzeRequest) -> AnalyzeResponse:
    """Briefing quotidien à partir du contexte ferme réel (pas de mock)."""
    if not settings.mistral_api_key:
        raise HTTPException(
            status_code=500,
            detail="MISTRAL_API_KEY is missing. Please set it in the .env file.",
        )
    try:
        return run_analysis(request)
    except RuntimeError as exc:
        raise HTTPException(status_code=500, detail=str(exc)) from exc
