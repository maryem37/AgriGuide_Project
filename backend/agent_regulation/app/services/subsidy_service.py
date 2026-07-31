"""Service de recherche et d'extraction structurée des aides financières agricoles.

Ne crée ni nouveau moteur de recherche ni nouvelle base vectorielle : réutilise
le service de recherche web existant (`web_search_service`, Tavily) pour trouver
des pages pertinentes, filtre celles qui ressemblent réellement à une aide, puis
utilise un LLM Mistral (sortie structurée) pour extraire et normaliser les
informations de chaque aide identifiée.
"""

from functools import lru_cache
from urllib.parse import urlparse

from langchain_core.messages import HumanMessage, SystemMessage
from langchain_mistralai import ChatMistralAI
from pydantic import BaseModel

from app.config.settings import get_settings
from app.schemas.subsidy import SubsidyInfo, SubsidySearchResponse
from app.schemas.web_search import WebSearchResult
from app.services.web_search_service import is_official_source, search_agricultural_web

SUBSIDY_KEYWORDS = [
    "aide",
    "subvention",
    "appel à projets",
    "appel a projet",
    "dispositif",
    "financement",
    "dotation",
    "dja",
    "feader",
    "pac",
    "soutien financier",
]

QUERY_TEMPLATES = [
    "aide financière subvention agricole {question}",
    "appel à projets agricole {question}",
]

EXTRACTION_SYSTEM_PROMPT = (
    "Tu extrais des informations sur des aides financières agricoles (subventions, "
    "appels à projets, dispositifs de soutien) à partir de résultats de recherche "
    "web fournis ci-dessous. Pour chaque aide clairement identifiable, renseigne les "
    "champs demandés en te basant UNIQUEMENT sur le texte fourni — n'invente rien. "
    "Si une information n'est pas présente dans le texte, laisse le champ vide "
    "(null). Si un extrait ne décrit pas une aide financière réelle et concrète "
    "(ex. simple actualité, article générique sans dispositif précis), ignore-le "
    "complètement. Pour chaque aide retenue, reprends exactement l'URL source "
    "(`source_url`) et le nom de domaine (`source_officielle`) de l'extrait dont "
    "elle provient."
)


class _ExtractionOutput(BaseModel):
    """Sortie structurée intermédiaire du LLM d'extraction."""

    subsidies: list[SubsidyInfo]


def _looks_like_subsidy(text: str) -> bool:
    """Filtre heuristique : le texte évoque-t-il une aide/subvention agricole ?"""
    lowered = text.lower()
    return any(keyword in lowered for keyword in SUBSIDY_KEYWORDS)


def _collect_candidate_results(question: str) -> list[WebSearchResult]:
    """Interroge le service web existant avec plusieurs formulations de requête,

    déduplique par URL et ne garde que les résultats qui ressemblent à une aide.
    """
    seen_urls: set[str] = set()
    candidates: list[WebSearchResult] = []
    for template in QUERY_TEMPLATES:
        query = template.format(question=question)
        response = search_agricultural_web(query)
        for result in response.results:
            if result.url in seen_urls:
                continue
            if not _looks_like_subsidy(f"{result.title} {result.snippet}"):
                continue
            seen_urls.add(result.url)
            candidates.append(result)
    return candidates


@lru_cache
def _get_extraction_llm():
    """Retourne le LLM d'extraction structurée (mis en cache)."""
    settings = get_settings()
    llm = ChatMistralAI(model="mistral-small-latest", mistral_api_key=settings.mistral_api_key, temperature=0)
    return llm.with_structured_output(_ExtractionOutput)


def _apply_official_flag(subsidies: list[SubsidyInfo]) -> None:
    """Recalcule `is_official` à partir du domaine réel de `source_url` (ne fait

    pas confiance au jugement du LLM sur ce point).
    """
    for subsidy in subsidies:
        domain = urlparse(subsidy.source_url).netloc.removeprefix("www.")
        subsidy.is_official = is_official_source(domain) if domain else False


def search_subsidies(question: str) -> SubsidySearchResponse:
    """Recherche des aides financières agricoles pertinentes pour la question posée.

    Construit plusieurs requêtes web ciblées (aide/subvention, appel à projets),
    filtre les résultats qui ressemblent réellement à une aide, puis utilise un
    LLM pour extraire et structurer les informations de chaque aide identifiée.
    """
    candidates = _collect_candidate_results(question)
    if not candidates:
        return SubsidySearchResponse(query=question, subsidies=[])

    sources_text = "\n\n".join(
        f"URL: {c.url}\nDomaine: {c.source}\nTitre: {c.title}\nContenu: {c.snippet}" for c in candidates
    )

    extractor = _get_extraction_llm()
    messages = [
        SystemMessage(content=EXTRACTION_SYSTEM_PROMPT),
        HumanMessage(content=f"Question de l'utilisateur : {question}\n\nRésultats web :\n\n{sources_text}"),
    ]
    output: _ExtractionOutput = extractor.invoke(messages)
    _apply_official_flag(output.subsidies)
    return SubsidySearchResponse(query=question, subsidies=output.subsidies)
