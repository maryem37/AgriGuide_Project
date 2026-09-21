"""Tests unitaires du service de génération de rapports HTML du risque climatique."""

import pytest
from app.models.schemas import ClimateRiskRequest
from app.services.climate_risk_service import calculate_climate_risk
from app.services.report_generator_service import (
    _generate_svg_indicator_chart,
    _vulgarized_explanation,
    generate_climate_risk_html_report,
)


def test_generate_svg_indicator_chart():
    svg = _generate_svg_indicator_chart(-1.4, -1.8, 0.25)
    assert "<svg" in svg
    assert "SPI (Pluie)" in svg
    assert "SPEI (Hydrique)" in svg
    assert "NDVI Decay" in svg


def test_vulgarized_explanation_dynamic():
    exp_severe = _vulgarized_explanation(-1.5, -1.6, 0.25)
    assert "Déficit pluviométrique sévère" in exp_severe["spi"]
    assert "Bilan hydrique (Pluie - ETP) fortement négatif" in exp_severe["spei"]
    assert "Décrochage significatif" in exp_severe["ndvi"]

    exp_normal = _vulgarized_explanation(0.5, 0.2, 0.02)
    assert "satisfaisant" in exp_normal["spi"]
    assert "équilibré" in exp_normal["spei"]
    assert "stables" in exp_normal["ndvi"]


def test_generate_climate_risk_html_report_sections():
    req = ClimateRiskRequest(
        lat=48.85,
        lon=2.35,
        crop_type="ble_tendre",
        parcel_id="PARCEL-REPORT-TEST",
        ndvi_current=0.62,
        ndvi_max_baseline=0.85,
    )
    risk_response = calculate_climate_risk(req)
    html_doc = generate_climate_risk_html_report(risk_response)

    assert "<!DOCTYPE html>" in html_doc
    assert "PARCEL-REPORT-TEST" in html_doc
    assert "Synthèse Exécutive" in html_doc
    assert "<svg" in html_doc
    assert "Matrice de Décomposition" in html_doc
    assert "Orientation Assurance Récolte" in html_doc
    assert "Belhsen et al." in html_doc
    assert "2026" in html_doc
    assert "Avertissement &amp; Cadre Légal" in html_doc or "Avertissement" in html_doc
