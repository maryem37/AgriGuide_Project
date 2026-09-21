"""FastAPI Router for Risk Analyst Agent (Port 8010)."""

from fastapi import APIRouter, HTTPException
from fastapi.responses import HTMLResponse

from app.models.schemas import (
    ClimateRiskRequest,
    ClimateRiskResponse,
    CropMixRequest,
    CropMixResponse,
)
from app.services.climate_risk_service import calculate_climate_risk
from app.services.crop_mix_service import optimize_crop_mix
from app.services.report_generator_service import generate_climate_risk_html_report

router = APIRouter(prefix="/risk", tags=["risk"])


@router.post("/climate", response_model=ClimateRiskResponse)
def evaluer_risque_climatique(req: ClimateRiskRequest) -> ClimateRiskResponse:
    """
    Calcule le score de risque climatique paramétrique (0-100) par parcelle
    basé sur les indices SPI (loi Gamma), SPEI (Pearson III) et le décrément NDVI.
    Fournit une recommandation d'assurance récolte avec prime indicative V1.
    Réf académique : Belhsen et al. (2026, JRACR, doi:10.54560/jracr.v16i2.726).
    """
    return calculate_climate_risk(req)


@router.post("/climate/report", response_class=HTMLResponse)
def generer_rapport_risque_climatique_html(req: ClimateRiskRequest) -> HTMLResponse:
    """
    Génère un rapport HTML5/CSS3 autonome d'aide à la décision en 8 sections
    avec graphiques SVG natifs, prêt pour la prévisualisation et l'impression PDF.
    Réf académique : Belhsen et al. (2026, JRACR).
    """
    risk_response = calculate_climate_risk(req)
    html_content = generate_climate_risk_html_report(risk_response)
    return HTMLResponse(content=html_content, status_code=200)


@router.post("/crop-mix", response_model=CropMixResponse)
def optimiser_asassolement_parcelle(req: CropMixRequest) -> CropMixResponse:
    """
    Optimise la répartition d'hectares (asassolement) sur l'exploitation via
    programmation linéaire (scipy.optimize.linprog) pour maximiser le profit global
    sous contraintes de budget, surface et plafonnement anti-monoculture (50% max).
    Calcule l'indice Herfindahl-Hirschman (HHI) de diversification.
    """
    return optimize_crop_mix(req)
