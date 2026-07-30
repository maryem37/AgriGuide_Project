"""Outil de recherche web pour trouver de nouvelles aides financières ou procédures.

Utilisé par l'agent lorsque l'information n'est pas disponible dans la base
réglementaire locale (RAG) et nécessite une recherche externe à jour : nouvelles
aides, appels à projets, subventions, procédures, formulaires, réglementations
récentes (PAC, national, régional, européen).

L'outil ne rédige pas de réponse : il retourne des résultats structurés
(titre, source, URL, extrait, date) que l'agent (LLM) se charge de synthétiser.
"""

import time

from langchain_core.tools import tool

from app.services.web_search_service import WebSearchResponse, is_official_source, search_agricultural_web

SNIPPET_MAX_CHARS = 500


def _truncate_snippet(text: str, max_chars: int = SNIPPET_MAX_CHARS) -> str:
    """Tronque un extrait à `max_chars` avec une coupure propre (mot entier)."""
    if len(text) <= max_chars:
        return text
    truncated = text[:max_chars].rsplit(" ", 1)[0]
    return truncated + "…"


def _format_results(response: WebSearchResponse) -> str:
    if not response.results:
        return "Aucun résultat web pertinent n'a été trouvé."

    blocks = []
    for i, result in enumerate(response.results, start=1):
        date_part = f" — {result.published_date}" if result.published_date else ""
        fiabilite = "Source officielle" if is_official_source(result.source) else "Source non officielle (à vérifier)"
        blocks.append(
            f"[W{i}] {result.title}\n"
            f"{fiabilite} : {result.source}{date_part}\n"
            f"URL : {result.url}\n"
            f"Extrait : {_truncate_snippet(result.snippet)}"
        )
    return "\n\n".join(blocks)


@tool
def recherche_web_aides_agricoles(question: str) -> str:
    """Recherche sur le web des informations récentes et actuelles concernant les
    aides financières, appels à projets, subventions, procédures administratives,
    formulaires et réglementations agricoles (PAC, national, régional, européen),
    en priorisant les sources officielles (agriculture.gouv.fr, legifrance.gouv.fr,
    franceagrimer.fr, asp-public.fr, service-public.fr, sites des Régions,
    institutions européennes).
    """
    start = time.perf_counter()
    response = search_agricultural_web(question)
    result = _format_results(response)
    print(f"[PERF] Web search: {time.perf_counter() - start:.2f}s")
    return result
