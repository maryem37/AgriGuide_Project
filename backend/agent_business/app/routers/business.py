from fastapi import APIRouter, Depends, HTTPException
from fastapi.responses import HTMLResponse

from app.models.schemas import (
    BusinessAdvisorRequest,
    BusinessAdvisorResponse,
    ClimateRiskRequest,
    ClimateRiskResponse,
    CropMixRequest,
    CropMixResponse,
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
    get_owned_terrains_total_area,
    save_scenarios,
)
from app.security import get_current_user_id

router = APIRouter(prefix="/business", tags=["business"])


def _authoritative_area(terrain_ids: list[str], user_id: str) -> float | None:
    if len(terrain_ids) <= 1:
        return get_owned_terrain_area(terrain_ids[0], user_id) if terrain_ids else None
    return get_owned_terrains_total_area(terrain_ids, user_id)


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
        terrain_ids = request.resolved_terrain_ids()
        terrain_area = _authoritative_area(terrain_ids, user_id)
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
        terrain_ids = request.resolved_terrain_ids()
        terrain_area = _authoritative_area(terrain_ids, user_id)
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


@router.post("/climate-risk", response_model=ClimateRiskResponse)
def evaluer_risque_climatique_parcelle(
    request: ClimateRiskRequest,
) -> ClimateRiskResponse:
    """
    Calcule le score de risque climatique paramétrique (0-100) par parcelle
    basé sur les indices SPI (loi Gamma), SPEI (Pearson III) et le décrément NDVI.
    Fournit une recommandation d'assurance récolte avec prime indicative V1.
    """
    from app.services.climate_risk_service import calculate_climate_risk
    return calculate_climate_risk(request)


@router.post("/crop-mix", response_model=CropMixResponse)
def optimiser_asassolement_parcelle(
    request: CropMixRequest,
) -> CropMixResponse:
    """
    Optimise la répartition d'hectares (asassolement) sur l'exploitation via
    programmation linéaire (scipy.optimize.linprog) pour maximiser le profit global
    sous contraintes de budget, surface et plafonnement anti-monoculture (50% max).
    Calcule l'indice Herfindahl-Hirschman (HHI) de diversification.
    """
    from app.services.crop_mix_service import optimize_crop_mix
    return optimize_crop_mix(request)


@router.post("/climate-risk/report", response_class=HTMLResponse)
def generer_rapport_risque_climatique_html(
    request: ClimateRiskRequest,
) -> HTMLResponse:
    """
    Génère un rapport HTML5/CSS3 autonome d'aide à la décision en 8 sections
    avec graphiques SVG natifs, prêt pour la prévisualisation et l'impression PDF.
    Réf : Belhsen et al. (2026, JRACR).
    """
    from fastapi.responses import HTMLResponse
    from app.services.climate_risk_service import calculate_climate_risk
    from app.services.report_generator_service import generate_climate_risk_html_report
    
    risk_response = calculate_climate_risk(request)
    html_content = generate_climate_risk_html_report(risk_response)
    return HTMLResponse(content=html_content, status_code=200)



