"""Schémas Pydantic pour les aides financières agricoles (subventions, appels à projets)."""

import re
from datetime import date, datetime

from pydantic import BaseModel, field_validator

# Doit rester synchronisé avec `subsidies.region VARCHAR(100)` (database/schema.sql).
REGION_MAX_LENGTH = 100

# Sépare un nom de région d'un texte accolé par erreur par le LLM (ex.
# "Occitanie - aide destinée aux jeunes agriculteurs..."). Un tiret SANS
# espace autour (nom de région composé : "Nouvelle-Aquitaine",
# "Hauts-de-France", "Île-de-France") n'est jamais coupé — uniquement un
# séparateur entouré d'au moins un espace, ou une parenthèse ouvrante.
_REGION_SEPARATOR_PATTERN = re.compile(r"\s+[-–—:;]\s*|\s*\(")


def _clean_region(value: str | None) -> str | None:
    """Nettoie une valeur `region` : ne doit contenir QUE la zone géographique
    (ex. "Occitanie", "France"), jamais une description ou une phrase
    d'éligibilité accolée par erreur par l'extraction LLM.

    Ne tronque JAMAIS silencieusement (un `[:100]` couperait au milieu d'un
    mot et masquerait une erreur d'extraction en amont) : essaie d'abord de
    ne garder que le segment avant un séparateur de phrase, et retourne
    `None` — plutôt qu'une valeur suspecte ou trop longue pour la colonne —
    si le résultat n'est toujours pas exploitable.
    """
    if value is None:
        return None

    cleaned = re.sub(r"\s+", " ", value).strip()
    if not cleaned:
        return None

    leading_segment = _REGION_SEPARATOR_PATTERN.split(cleaned, maxsplit=1)[0].strip()
    cleaned = leading_segment or cleaned

    if not cleaned or len(cleaned) > REGION_MAX_LENGTH:
        return None

    return cleaned


class SubsidyInfo(BaseModel):
    """Une aide financière agricole, normalisée à partir de résultats web."""

    nom: str
    organisme: str | None = None
    type_aide: str | None = None
    objectif: str | None = None
    beneficiaires: str | None = None
    conditions_eligibilite: str | None = None
    montant: str | None = None
    depenses_eligibles: str | None = None
    region: str | None = None
    date_ouverture: str | None = None
    date_limite: str | None = None
    statut: str | None = None  # 'ouvert' | 'fermé' — uniquement si explicite dans la source, sinon None
    procedure: str | None = None
    documents_necessaires: str | None = None
    source_officielle: str
    source_url: str
    is_official: bool = False

    @field_validator("region")
    @classmethod
    def _clean_region_field(cls, value: str | None) -> str | None:
        return _clean_region(value)


class SubsidySearchResponse(BaseModel):
    """Ensemble des aides trouvées pour une question donnée."""

    query: str
    subsidies: list[SubsidyInfo]


# ---------------------------------------------------------------------------
# Aides financières stockées en base (table `subsidies`) — voir
# `app/services/subsidy_store_service.py` et `app/services/subsidy_sync_service.py`.
# ---------------------------------------------------------------------------


class SubsidyUpsertInput(BaseModel):
    """Champs nécessaires pour insérer/mettre à jour une aide en base.

    Dates déjà normalisées (contrairement à `SubsidyInfo.date_limite`, qui est
    du texte libre issu de l'extraction LLM) — voir `subsidy_sync_service._parse_date`.
    """

    name: str
    description: str | None = None
    eligibility: str | None = None
    amount: str | None = None
    region: str | None = None
    start_date: date | None = None
    end_date: date | None = None
    application_procedure: str | None = None
    source_name: str
    source_url: str
    is_official: bool = False

    @field_validator("region")
    @classmethod
    def _clean_region_field(cls, value: str | None) -> str | None:
        # Filet de sécurité supplémentaire juste avant l'insertion en base
        # (`subsidies.region VARCHAR(100)`), même nettoyage que `SubsidyInfo.region`.
        return _clean_region(value)


class Subsidy(BaseModel):
    """Une aide financière telle que stockée en base (table `subsidies`)."""

    id: str
    name: str
    description: str | None = None
    eligibility: str | None = None
    amount: str | None = None
    region: str | None = None
    start_date: date | None = None
    end_date: date | None = None
    application_procedure: str | None = None
    source_name: str
    source_url: str
    is_official: bool = False
    last_verified_at: datetime
    created_at: datetime
    updated_at: datetime


class SubsidyListResponse(BaseModel):
    """Réponse de `GET /subsidies` — aides actives triées par échéance la plus proche."""

    subsidies: list[Subsidy]


class SubsidySyncResult(BaseModel):
    """Résumé d'une synchronisation des aides (voir `subsidy_sync_service.sync_subsidies`)."""

    total_found: int
    created: int
    updated: int
