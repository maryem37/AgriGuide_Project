"""Outil de recherche d'aides financières agricoles (subventions, appels à projets).

Réutilise le service de recherche web existant (Tavily, via `subsidy_service` /
`web_search_service`) pour trouver des dispositifs d'aide, puis retourne une
liste structurée (organisme, montant, éligibilité, dates, procédure, source...)
que l'agent (LLM) peut directement exploiter — sans rédiger de synthèse, laissée
au LLM de l'agent.
"""

import time

from langchain_core.tools import tool

from app.schemas.subsidy import SubsidyInfo, SubsidySearchResponse
from app.services.subsidy_service import search_subsidies

_FIELD_LABELS: list[tuple[str, str]] = [
    ("organisme", "Organisme"),
    ("type_aide", "Type d'aide"),
    ("objectif", "Objectif"),
    ("beneficiaires", "Bénéficiaires"),
    ("conditions_eligibilite", "Conditions d'éligibilité"),
    ("montant", "Montant / taux de financement"),
    ("depenses_eligibles", "Dépenses éligibles"),
    ("region", "Région"),
    ("date_ouverture", "Date d'ouverture"),
    ("date_limite", "Date limite"),
    ("procedure", "Procédure"),
    ("documents_necessaires", "Documents nécessaires"),
]


def _format_subsidy(index: int, subsidy: SubsidyInfo) -> str:
    fiabilite = "Source officielle" if subsidy.is_official else "Source non officielle (à vérifier)"
    lines = [f"[S{index}] {subsidy.nom}"]
    for field, label in _FIELD_LABELS:
        value = getattr(subsidy, field)
        if value:
            lines.append(f"{label} : {value}")
    lines.append(f"{fiabilite} : {subsidy.source_officielle}")
    lines.append(f"URL : {subsidy.source_url}")
    return "\n".join(lines)


def _format_response(response: SubsidySearchResponse) -> str:
    if not response.subsidies:
        return "Aucune aide financière agricole correspondante n'a été trouvée."
    return "\n\n".join(_format_subsidy(i, s) for i, s in enumerate(response.subsidies, start=1))


@tool
def recherche_aides_financieres_agricoles(question: str) -> str:
    """Recherche des aides financières agricoles, subventions et appels à projets
    (nationaux, régionaux, européens) correspondant à la question posée : type de
    bénéficiaire (ex. jeune agriculteur), investissement visé (ex. irrigation),
    région, période. Retourne pour chaque aide trouvée ses caractéristiques
    structurées (organisme, montant, éligibilité, dates, procédure, source).
    """
    start = time.perf_counter()
    response = search_subsidies(question)
    result = _format_response(response)
    print(f"[PERF] Subsidy search: {time.perf_counter() - start:.2f}s")
    return result
