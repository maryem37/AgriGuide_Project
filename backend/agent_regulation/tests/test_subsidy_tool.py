"""Tests du tool #3 (aides financières agricoles).

Tests unitaires (aucun appel réseau) sur le filtre de pertinence et les
schémas, puis un test réel (nécessite MISTRAL_API_KEY et WEB_SEARCH_API_KEY)
qui recherche une véritable aide agricole de bout en bout.
"""

import os
import sys

import pytest
from dotenv import load_dotenv

load_dotenv()

if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")

from app.schemas.subsidy import SubsidyInfo, SubsidySearchResponse
from app.services.subsidy_service import _looks_like_subsidy
from app.tools.subsidy_tool import _format_response, recherche_aides_financieres_agricoles


def test_looks_like_subsidy_detects_relevant_keywords():
    assert _looks_like_subsidy("Une nouvelle subvention pour les jeunes agriculteurs")
    assert _looks_like_subsidy("Appel à projets FEADER 2026")
    assert not _looks_like_subsidy("Le temps sera pluvieux demain sur la région")


def test_subsidy_info_allows_missing_optional_fields():
    subsidy = SubsidyInfo(
        nom="Dotation Jeune Agriculteur",
        source_officielle="agriculture.gouv.fr",
        source_url="https://agriculture.gouv.fr/dja",
    )
    assert subsidy.montant is None
    assert subsidy.is_official is False


def test_format_response_handles_empty_results():
    response = SubsidySearchResponse(query="test", subsidies=[])
    assert "Aucune aide" in _format_response(response)


def test_format_response_includes_key_fields():
    response = SubsidySearchResponse(
        query="test",
        subsidies=[
            SubsidyInfo(
                nom="Dotation Jeune Agriculteur",
                organisme="État",
                montant="entre 10 000 et 40 000 €",
                source_officielle="agriculture.gouv.fr",
                source_url="https://agriculture.gouv.fr/dja",
                is_official=True,
            )
        ],
    )
    formatted = _format_response(response)
    assert "[S1] Dotation Jeune Agriculteur" in formatted
    assert "Montant / taux de financement : entre 10 000 et 40 000 €" in formatted
    assert "Source officielle : agriculture.gouv.fr" in formatted
    assert "https://agriculture.gouv.fr/dja" in formatted


pytestmark_real = pytest.mark.skipif(
    not os.getenv("WEB_SEARCH_API_KEY") or not os.getenv("MISTRAL_API_KEY"),
    reason="WEB_SEARCH_API_KEY et MISTRAL_API_KEY nécessaires pour ce test réel.",
)


@pytestmark_real
def test_recherche_aides_financieres_agricoles_real_search():
    output = recherche_aides_financieres_agricoles.invoke(
        "Quelles aides sont disponibles pour un jeune agriculteur ?"
    )
    print("\n" + output)

    assert isinstance(output, str) and len(output) > 0
    assert "Aucune aide" not in output, "Aucune aide trouvée — vérifier la requête ou les clés API."
    assert "[S1]" in output
