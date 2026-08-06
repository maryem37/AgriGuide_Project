"""Tests du tool #3 (aides financières agricoles).

Tests unitaires (aucun appel réseau) sur le filtre de pertinence et les
schémas, puis un test réel (nécessite MISTRAL_API_KEY et WEB_SEARCH_API_KEY)
qui recherche une véritable aide agricole de bout en bout.
"""

import os
import sys
from datetime import date, timedelta

import pytest
from dotenv import load_dotenv

load_dotenv()

if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")

from app.schemas.subsidy import SubsidyInfo, SubsidySearchResponse
from app.services.subsidy_service import (
    _filter_and_rank_open_subsidies,
    _looks_like_subsidy,
    _parse_subsidy_date,
)
from app.tools.subsidy_tool import _format_response, recherche_aides_financieres_agricoles


def _future_date_str(days: int) -> str:
    """Date au format DD/MM/YYYY, relative à aujourd'hui (évite les dates codées
    en dur qui finissent par se retrouver dans le passé)."""
    d = date.today() + timedelta(days=days)
    return d.strftime("%d/%m/%Y")


def _past_date_str(days: int) -> str:
    d = date.today() - timedelta(days=days)
    return d.strftime("%d/%m/%Y")


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


# ---------------------------------------------------------------------------
# `region` — doit contenir UNIQUEMENT la zone géographique (jamais une
# description accolée par erreur par l'extraction LLM), sans jamais dépasser
# `subsidies.region VARCHAR(100)` (database/schema.sql).
# ---------------------------------------------------------------------------


def _subsidy_with_region(region: str | None) -> SubsidyInfo:
    return SubsidyInfo(
        nom="Aide test",
        region=region,
        source_officielle="agriculture.gouv.fr",
        source_url="https://agriculture.gouv.fr/aide-test",
    )


def test_region_field_strips_description_wrongly_appended_by_llm():
    """Cas rapporté : le LLM colle une description après le nom de la région."""
    subsidy = _subsidy_with_region(
        "Occitanie - aide destinée aux jeunes agriculteurs souhaitant s'installer"
    )
    assert subsidy.region == "Occitanie"


def test_region_field_keeps_national_region_unchanged():
    subsidy = _subsidy_with_region("France")
    assert subsidy.region == "France"


def test_region_field_preserves_hyphenated_region_names():
    """Un tiret SANS espace autour fait partie du nom de la région — ne doit
    jamais être coupé (contrairement à un tiret séparateur de phrase, entouré
    d'espaces)."""
    assert _subsidy_with_region("Nouvelle-Aquitaine").region == "Nouvelle-Aquitaine"
    assert _subsidy_with_region("Hauts-de-France").region == "Hauts-de-France"
    assert _subsidy_with_region("Île-de-France").region == "Île-de-France"


def test_region_field_keeps_short_multi_region_list():
    assert _subsidy_with_region("Occitanie, Nouvelle-Aquitaine").region == "Occitanie, Nouvelle-Aquitaine"


def test_region_field_strips_surrounding_whitespace():
    assert _subsidy_with_region("  Bretagne  ").region == "Bretagne"


def test_region_field_becomes_none_when_unsalvageably_long():
    """Aucun séparateur exploitable et bien au-delà de VARCHAR(100) : doit
    devenir `None` plutôt que d'être tronqué silencieusement (ce qui
    masquerait l'erreur d'extraction) ou de faire échouer la validation."""
    subsidy = _subsidy_with_region("Zone rurale " * 20)  # ~240 caractères, sans séparateur
    assert subsidy.region is None


def test_region_field_none_stays_none():
    assert _subsidy_with_region(None).region is None


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


def test_parse_subsidy_date_handles_common_formats():
    assert _parse_subsidy_date("31/07/2026") == date(2026, 7, 31)
    assert _parse_subsidy_date("2026-07-31") == date(2026, 7, 31)
    assert _parse_subsidy_date(None) is None
    assert _parse_subsidy_date("jusqu'à épuisement des crédits") is None


def test_filter_excludes_subsidy_with_past_end_date():
    expired = SubsidyInfo(
        nom="Ancienne aide",
        date_limite=_past_date_str(30),
        source_officielle="agriculture.gouv.fr",
        source_url="https://agriculture.gouv.fr/ancienne-aide",
    )
    assert _filter_and_rank_open_subsidies([expired]) == []


def test_filter_excludes_explicitly_closed_subsidy_even_without_parseable_date():
    closed = SubsidyInfo(
        nom="Aide close",
        statut="fermé",
        date_limite="candidatures closes",
        source_officielle="agriculture.gouv.fr",
        source_url="https://agriculture.gouv.fr/aide-close",
    )
    assert _filter_and_rank_open_subsidies([closed]) == []


def test_filter_keeps_subsidy_with_no_identifiable_end_date():
    undated = SubsidyInfo(
        nom="Aide sans échéance connue",
        source_officielle="agriculture.gouv.fr",
        source_url="https://agriculture.gouv.fr/aide-vague",
    )
    result = _filter_and_rank_open_subsidies([undated])
    assert [s.nom for s in result] == ["Aide sans échéance connue"]


def test_filter_prioritizes_open_dated_subsidy_over_undated_one():
    """Une aide 2026 encore ouverte, avec échéance connue, doit être prioritaire
    sur une aide ancienne / mal datée (sans date limite identifiable)."""
    undated_old = SubsidyInfo(
        nom="Aide ancienne mal datée",
        source_officielle="agriculture.gouv.fr",
        source_url="https://agriculture.gouv.fr/aide-vague",
    )
    open_2026 = SubsidyInfo(
        nom="Aide 2026 ouverte",
        date_limite=_future_date_str(90),
        source_officielle="franceagrimer.fr",
        source_url="https://www.franceagrimer.fr/aide-2026",
    )
    result = _filter_and_rank_open_subsidies([undated_old, open_2026])
    assert [s.nom for s in result] == ["Aide 2026 ouverte", "Aide ancienne mal datée"]


def test_filter_ranks_open_subsidies_by_nearest_deadline_first():
    near = SubsidyInfo(
        nom="Aide échéance proche",
        date_limite=_future_date_str(5),
        source_officielle="agriculture.gouv.fr",
        source_url="https://agriculture.gouv.fr/aide-proche",
    )
    far = SubsidyInfo(
        nom="Aide échéance lointaine",
        date_limite=_future_date_str(120),
        source_officielle="agriculture.gouv.fr",
        source_url="https://agriculture.gouv.fr/aide-lointaine",
    )
    result = _filter_and_rank_open_subsidies([far, near])
    assert [s.nom for s in result] == ["Aide échéance proche", "Aide échéance lointaine"]


def test_format_response_marks_missing_deadline_explicitly():
    """Une aide sans date limite connue ne doit jamais laisser croire à une
    échéance certaine — cf. ligne de repli explicite dans `_format_subsidy`."""
    response = SubsidySearchResponse(
        query="test",
        subsidies=[
            SubsidyInfo(
                nom="Aide sans échéance connue",
                source_officielle="agriculture.gouv.fr",
                source_url="https://agriculture.gouv.fr/aide-vague",
            )
        ],
    )
    formatted = _format_response(response)
    assert "Date limite : non précisée" in formatted


def test_format_response_includes_statut_when_present():
    response = SubsidySearchResponse(
        query="test",
        subsidies=[
            SubsidyInfo(
                nom="Aide test",
                statut="ouvert",
                date_limite=_future_date_str(30),
                source_officielle="agriculture.gouv.fr",
                source_url="https://agriculture.gouv.fr/aide-test",
            )
        ],
    )
    formatted = _format_response(response)
    assert "Statut : ouvert" in formatted


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
