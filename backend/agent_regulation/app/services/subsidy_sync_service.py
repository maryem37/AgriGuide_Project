"""Synchronisation des aides financières agricoles vers la table `subsidies`.

Ne crée aucun nouveau moteur de recherche : réutilise tel quel le Subsidy
Search existant (`app.services.subsidy_service.search_subsidies`, Tool #3),
puis normalise et stocke chaque aide trouvée via `subsidy_store_service`.

Ne met en place aucun scheduler ici (pas de Celery Beat) : `sync_subsidies`
est une fonction simple, prête à être appelée à la demande (endpoint
`POST /subsidies/sync`) ou plus tard depuis une tâche planifiée.
"""

import re
from datetime import date

from app.schemas.subsidy import SubsidyInfo, SubsidySyncResult, SubsidyUpsertInput
from app.services import subsidy_store_service
from app.services.subsidy_service import search_subsidies

# Requêtes génériques utilisées quand la synchronisation n'est pas déclenchée
# pour une question précise (ex. appel quotidien futur). Volontairement large
# pour couvrir les principaux types d'aides agricoles françaises.
DEFAULT_SYNC_QUERIES = [
    "aides agricoles France",
    "subventions agricoles jeunes agriculteurs",
    "appel à projets agricole FranceAgriMer",
]

_MONTHS_FR = {
    "janvier": 1,
    "février": 2,
    "fevrier": 2,
    "mars": 3,
    "avril": 4,
    "mai": 5,
    "juin": 6,
    "juillet": 7,
    "août": 8,
    "aout": 8,
    "septembre": 9,
    "octobre": 10,
    "novembre": 11,
    "décembre": 12,
    "decembre": 12,
}

_DATE_PATTERNS = (
    re.compile(r"(\d{4})-(\d{2})-(\d{2})"),  # 2026-07-31
    re.compile(r"(\d{1,2})/(\d{1,2})/(\d{4})"),  # 31/07/2026
    re.compile(r"(\d{1,2})-(\d{1,2})-(\d{4})"),  # 31-07-2026
)
_DATE_TEXT_PATTERN = re.compile(
    r"(\d{1,2})\s+(" + "|".join(_MONTHS_FR) + r")\s+(\d{4})", re.IGNORECASE
)


def _parse_date(text: str | None) -> date | None:
    """Extrait une date à partir d'un texte libre (sortie LLM de `SubsidyInfo`).

    Reconnaît les formats numériques courants (YYYY-MM-DD, DD/MM/YYYY,
    DD-MM-YYYY) et les dates en toutes lettres en français ("31 juillet
    2026"). Best-effort uniquement : si aucun format connu n'est trouvé (ex.
    "jusqu'à épuisement des crédits"), retourne None plutôt que de deviner —
    l'aide est quand même stockée, juste sans date exploitable pour le tri.
    """
    if not text:
        return None

    match = _DATE_PATTERNS[0].search(text)
    if match:
        year, month, day = match.groups()
        return _safe_date(int(year), int(month), int(day))

    for pattern in _DATE_PATTERNS[1:]:
        match = pattern.search(text)
        if match:
            day, month, year = match.groups()
            return _safe_date(int(year), int(month), int(day))

    match = _DATE_TEXT_PATTERN.search(text)
    if match:
        day, month_name, year = match.groups()
        month = _MONTHS_FR.get(month_name.lower())
        if month:
            return _safe_date(int(year), month, int(day))

    return None


def _safe_date(year: int, month: int, day: int) -> date | None:
    try:
        return date(year, month, day)
    except ValueError:
        return None


def _to_upsert_input(info: SubsidyInfo) -> SubsidyUpsertInput:
    return SubsidyUpsertInput(
        name=info.nom,
        description=info.objectif,
        eligibility=info.conditions_eligibilite or info.beneficiaires,
        amount=info.montant,
        region=info.region,
        start_date=_parse_date(info.date_ouverture),
        end_date=_parse_date(info.date_limite),
        application_procedure=info.procedure,
        source_name=info.source_officielle,
        source_url=info.source_url,
        is_official=info.is_official,
    )


def sync_subsidies(queries: list[str] | None = None) -> SubsidySyncResult:
    """Recherche des aides via le Subsidy Search existant puis les stocke.

    Déduplique par `source_url` au sein d'une même synchronisation (une aide
    peut ressortir de plusieurs requêtes), puis délègue le "existe déjà ?
    créer/mettre à jour ?" à `subsidy_store_service.upsert_subsidy` (upsert
    SQL atomique sur `source_url`).
    """
    queries = queries or DEFAULT_SYNC_QUERIES

    seen_urls: set[str] = set()
    created = 0
    updated = 0

    for query in queries:
        response = search_subsidies(query)
        for info in response.subsidies:
            if info.source_url in seen_urls:
                continue
            seen_urls.add(info.source_url)

            result = subsidy_store_service.upsert_subsidy(_to_upsert_input(info))
            if result["was_created"]:
                created += 1
            else:
                updated += 1

    return SubsidySyncResult(total_found=len(seen_urls), created=created, updated=updated)
