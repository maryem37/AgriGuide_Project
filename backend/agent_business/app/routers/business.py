from fastapi import APIRouter, Depends, HTTPException

from app.models.schemas import (
    BusinessAdvisorRequest,
    BusinessAdvisorResponse,
    FarmerDecisionRequest,
    FarmerDecisionResponse,
)
from app.services.scenario_generator import generer_scenarios
from app.services.decision_service import confirmer_decision, AllocationInvalideError
from app.services.persistence_service import (
    PersistenceUnavailableError,
    database_persistence_enabled,
    get_latest_decision,
    get_owned_terrain_area,
    save_scenarios,
)
from app.security import get_current_user_id

router = APIRouter(prefix="/business", tags=["business"])


@router.post("/scenarios", response_model=BusinessAdvisorResponse)
def obtenir_scenarios(
    request: BusinessAdvisorRequest,
    user_id: str = Depends(get_current_user_id),
) -> BusinessAdvisorResponse:
    """
    Génère les N scénarios (3 par défaut) à partir des crop_recommendations
    de l'agent Agriculture + du budget fourni par le farmer.
    """
    try:
        terrain_area = get_owned_terrain_area(request.terrain_id, user_id)
        if database_persistence_enabled() and terrain_area is None:
            raise HTTPException(status_code=404, detail="Terrain introuvable ou non autorisé.")
        if terrain_area is not None:
            request = request.model_copy(update={"superficie_disponible_ha": terrain_area})
        scenarios = generer_scenarios(request)
        save_scenarios(scenarios)
    except PersistenceUnavailableError as exc:
        raise HTTPException(status_code=503, detail=str(exc))
    return BusinessAdvisorResponse(
        terrain_id=request.terrain_id,
        budget_input=request.budget_input,
        scenarios=scenarios,
    )


@router.post("/decision", response_model=FarmerDecisionResponse)
def confirmer_decision_farmer(
    request: FarmerDecisionRequest,
    user_id: str = Depends(get_current_user_id),
) -> FarmerDecisionResponse:
    """
    Human-in-the-loop : le farmer choisit sa répartition finale d'hectares
    parmi les scénarios proposés. Retourne le coût final et les dates de
    maturité prévues par culture (utilisées par l'agent Monitoring).
    """
    try:
        terrain_area = get_owned_terrain_area(request.terrain_id, user_id)
        if database_persistence_enabled() and terrain_area is None:
            raise HTTPException(status_code=404, detail="Terrain introuvable ou non autorisé.")
        if terrain_area is not None:
            request = request.model_copy(update={"superficie_disponible_ha": terrain_area})
        return confirmer_decision(request)
    except AllocationInvalideError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except PersistenceUnavailableError as e:
        raise HTTPException(status_code=503, detail=str(e))


@router.get("/decisions/{terrain_id}/latest", response_model=FarmerDecisionResponse)
def derniere_decision_farmer(
    terrain_id: str,
    user_id: str = Depends(get_current_user_id),
) -> FarmerDecisionResponse:
    """Contexte persistant consommable par l'agent Monitoring."""
    try:
        terrain_area = get_owned_terrain_area(terrain_id, user_id)
        if database_persistence_enabled() and terrain_area is None:
            raise HTTPException(status_code=404, detail="Terrain introuvable ou non autorisé.")
        decision = get_latest_decision(terrain_id)
    except PersistenceUnavailableError as exc:
        raise HTTPException(status_code=503, detail=str(exc))
    if decision is None:
        raise HTTPException(status_code=404, detail="Aucune décision confirmée pour ce terrain.")
    return decision
