"""
Modèles Pydantic de l'agent Business.

Alignés champ à champ sur database/schema.sql (business_scenarios,
farmer_decisions, decision_allocations) pour que la persistance en base
n'ait pas de mapping à réinventer.
"""

from __future__ import annotations
from datetime import date, datetime
from typing import Optional
from pydantic import BaseModel, Field, field_validator


# ---------------------------------------------------------------------------
# Entrées (ce que l'agent Business reçoit)
# ---------------------------------------------------------------------------

class CropRecommendation(BaseModel):
    """Reflète une ligne de crop_recommendations produite par l'agent Agriculture."""
    rang: int
    culture: str
    score_compatibilite: float = Field(ge=0, le=100)
    cycle_jours: int = Field(gt=0)
    besoins_irrigation: dict
    besoins_engrais: dict
    besoins_pesticides: dict
    feature_importance: dict


class BusinessAdvisorRequest(BaseModel):
    """Input du endpoint POST /business/scenarios"""
    terrain_id: str
    superficie_disponible_ha: float = Field(gt=0)
    budget_input: float = Field(gt=0)
    date_plantation_prevue: date
    crop_recommendations: list[CropRecommendation]
    nb_scenarios: int = Field(default=3, ge=1, le=5)


# ---------------------------------------------------------------------------
# Sortie intermédiaire (résultats des services avant assemblage)
# ---------------------------------------------------------------------------

class EtudeMarche(BaseModel):
    prix_moyen_eur_par_kg: float
    rendement_estime_kg_par_ha: float
    tendance_prix: float  # -1 à 1
    date_recolte_estimee: date
    profit_brut_par_ha: float
    source: str


class EtudeRisque(BaseModel):
    risque_principal: str
    description: str
    probabilite: float = Field(ge=0, le=1)
    impact: float = Field(ge=0, le=1)
    risque_score_normalise: float = Field(ge=0, le=1)  # probabilite * impact
    solution_mitigation: str
    cout_mitigation_eur_par_ha: float


# ---------------------------------------------------------------------------
# Explicabilité — détail des calculs, pour le bouton "Détails" côté frontend
# ---------------------------------------------------------------------------

class DetailCalculMetrique(BaseModel):
    """Explique comment une métrique du scénario a été obtenue : formule, valeurs
    intermédiaires utilisées, et sources des données d'entrée."""
    formule: str
    valeurs: dict
    sources: list[str]


class DetailCalculScenario(BaseModel):
    """Regroupe l'explication de chaque métrique affichée dans une carte scénario."""
    score_matching: DetailCalculMetrique
    surface_conseillee: DetailCalculMetrique
    rendement_estime: DetailCalculMetrique
    recolte_estimee: DetailCalculMetrique
    profit_estime: DetailCalculMetrique


# ---------------------------------------------------------------------------
# Sortie finale — reflète business_scenarios
# ---------------------------------------------------------------------------

class BusinessScenario(BaseModel):
    id: Optional[str] = None
    terrain_id: str
    budget_input: float
    culture: str
    quantite_par_ha: float
    profit_estime: float
    risque_score: float
    risque_description: str
    solution_risque: str
    matching_score: float = Field(ge=0, le=100)
    etude_marche: dict
    superficie_max_financable_ha: float  # combien d'ha ce budget permet de couvrir
    superficie_conseillee_ha: float  # min(disponible, max_financable) — surface réellement recommandée
    detail_calcul: DetailCalculScenario
    created_at: datetime = Field(default_factory=datetime.utcnow)


class BusinessAdvisorResponse(BaseModel):
    terrain_id: str
    budget_input: float
    scenarios: list[BusinessScenario]


# ---------------------------------------------------------------------------
# Human-in-the-loop — reflète farmer_decisions + decision_allocations
# ---------------------------------------------------------------------------

class AllocationChoisie(BaseModel):
    scenario_id: str
    culture: str
    hectares_alloues: float = Field(gt=0)

    @field_validator("hectares_alloues")
    @classmethod
    def hectares_positifs(cls, v: float) -> float:
        if v <= 0:
            raise ValueError("hectares_alloues doit être positif")
        return v


class FarmerDecisionRequest(BaseModel):
    """Input du endpoint POST /business/decision (confirmation du farmer)"""
    terrain_id: str
    allocations: list[AllocationChoisie]
    superficie_disponible_ha: float


class FarmerDecisionResponse(BaseModel):
    decision_id: str
    terrain_id: str
    statut: str  # 'confirmed'
    cout_final: float
    superficie_totale_allouee_ha: float
    allocations: list[dict]  # inclut date_maturite_prevue par culture
    created_at: datetime = Field(default_factory=datetime.utcnow)
