"""Test du tool #2 (recherche web) : vérifie qu'une recherche sur les aides
agricoles 2026 retourne des résultats structurés et exploitables.

Nécessite une clé Tavily valide dans WEB_SEARCH_API_KEY (.env) ; le test est
ignoré si la clé n'est pas configurée.
"""

import os
import sys

import pytest
from dotenv import load_dotenv

load_dotenv()

if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")

from app.services.web_search_service import search_agricultural_web
from app.tools.web_search_tool import recherche_web_aides_agricoles

QUESTION = "Quelles nouvelles aides agricoles sont disponibles en France en 2026 ?"

pytestmark = pytest.mark.skipif(
    not os.getenv("WEB_SEARCH_API_KEY"),
    reason="WEB_SEARCH_API_KEY non configurée (nécessaire pour interroger Tavily).",
)


def test_search_agricultural_web_returns_structured_results():
    response = search_agricultural_web(QUESTION)

    assert response.results, "Aucun résultat retourné par la recherche web."

    for i, result in enumerate(response.results, start=1):
        print(f"\n[{i}] {result.title}")
        print(f"    Source : {result.source}")
        print(f"    URL    : {result.url}")
        print(f"    Extrait: {result.snippet[:200]}")
        assert result.url.startswith("http")


def test_web_search_tool_formats_output_for_agent():
    output = recherche_web_aides_agricoles.invoke(QUESTION)
    print("\n" + output)
    assert isinstance(output, str) and len(output) > 0
