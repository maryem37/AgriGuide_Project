import pytest
from app.services.report_generator_service import generate_climate_risk_html_report
from app.models.schemas import ClimateRiskResponse, RiskBreakdown, InsuranceRecommendation

def test_generate_climate_risk_html_report():
    mock_risk = ClimateRiskResponse(
        parcel_id="PARCEL-456",
        crop_type="Blé tendre",
        risk_score=68,
        risk_level="ÉLEVÉ",
        risk_breakdown=RiskBreakdown(
            spi_3m=-1.65,
            spei_3m=-1.82,
            ndvi_decay=0.28,
            composite_index=-1.45,
            drought_component_score=96.5,
            vegetation_stress_score=28.0
        ),
        insurance_recommendation=InsuranceRecommendation(
            suggested_coverage="Couverture Paramétrique Sécheresse Intégrale",
            estimated_annual_premium_eur_ha=45.0,
            payout_trigger_threshold=-1.5,
            payout_exhaustion_threshold=-2.5,
            reasoning="Risque d'indemnisation élevé au vu du cumul déficitaire des précipitations."
        )
    )

    html_content = generate_climate_risk_html_report(mock_risk)

    assert "<!DOCTYPE html>" in html_content
    assert "PARCEL-456" in html_content
    assert "Blé tendre" in html_content
    assert "68" in html_content
    assert "ÉLEVÉ" in html_content
    assert "Belhsen et al. (2026, JRACR)" in html_content
    assert "<svg" in html_content
    assert "@media print" in html_content
