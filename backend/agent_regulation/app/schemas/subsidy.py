"""Schémas Pydantic pour les aides financières agricoles (subventions, appels à projets)."""

from pydantic import BaseModel


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
    procedure: str | None = None
    documents_necessaires: str | None = None
    source_officielle: str
    source_url: str
    is_official: bool = False


class SubsidySearchResponse(BaseModel):
    """Ensemble des aides trouvées pour une question donnée."""

    query: str
    subsidies: list[SubsidyInfo]
