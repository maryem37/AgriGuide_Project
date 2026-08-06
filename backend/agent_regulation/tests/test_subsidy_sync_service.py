"""Tests du parsing de dates du service de synchronisation des aides.

Tests unitaires purs (aucun réseau, aucune base de données).
"""

from datetime import date

from app.services.subsidy_sync_service import _parse_date


def test_parse_date_handles_iso_format():
    assert _parse_date("2026-07-31") == date(2026, 7, 31)


def test_parse_date_handles_french_slash_format():
    assert _parse_date("Jusqu'au 31/07/2026") == date(2026, 7, 31)


def test_parse_date_handles_french_dash_format():
    assert _parse_date("31-07-2026") == date(2026, 7, 31)


def test_parse_date_handles_french_text_format():
    assert _parse_date("avant le 31 juillet 2026") == date(2026, 7, 31)
    assert _parse_date("1 mars 2026") == date(2026, 3, 1)


def test_parse_date_returns_none_when_missing_or_unparseable():
    assert _parse_date(None) is None
    assert _parse_date("") is None
    assert _parse_date("jusqu'à épuisement des crédits") is None


def test_parse_date_returns_none_for_invalid_calendar_date():
    assert _parse_date("31/02/2026") is None
