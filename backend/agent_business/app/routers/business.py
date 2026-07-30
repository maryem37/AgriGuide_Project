from fastapi import APIRouter, HTTPException

from app.models.schemas import (
    BusinessAdvisorRequest,
    BusinessAdvisorResponse,
    FarmerDecisionRequest,
    FarmerDecisionResponse,
)
from app.services.scenario_generator import generer_scenarios
from app.services.decision_service import confirmer_decision, AllocationInvalideError

router = APIRouter(prefix="/business", tags=["business"])


@router.post("/scenarios", response_model=BusinessAdvisorResponse)
def obtenir_scenarios(request: BusinessAdvisorRequest) -> BusinessAdvisorResponse:
    """
    Génère les N scénarios (3 par défaut) à partir des crop_recommendations
    de l'agent Agriculture + du budget fourni par le farmer.
    """
    scenarios = generer_scenarios(request)
    return BusinessAdvisorResponse(
        terrain_id=request.terrain_id,
        budget_input=request.budget_input,
        scenarios=scenarios,
    )


@router.post("/decision", response_model=FarmerDecisionResponse)
def confirmer_decision_farmer(request: FarmerDecisionRequest) -> FarmerDecisionResponse:
    """
    Human-in-the-loop : le farmer choisit sa répartition finale d'hectares
    parmi les scénarios proposés. Retourne le coût final et les dates de
    maturité prévues par culture (utilisées par l'agent Monitoring).
    """
    try:
        return confirmer_decision(request)
    except AllocationInvalideError as e:
        raise HTTPException(status_code=400, detail=str(e))
