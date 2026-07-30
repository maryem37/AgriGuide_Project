"""
Service Scoring.

Le matching score équilibre Budget / Étude de marché / Étude de risque.
Formule (documentée aussi dans backend/agent_business/README.md) :

    score = w1 * profit_normalise + w2 * (1 - risque_normalise) + w3 * fit_budget

- profit_normalise : profit net par ha, normalisé min-max sur l'ensemble
  des cultures candidates (0 = la moins rentable du lot, 1 = la plus rentable)
- risque_normalise : probabilite * impact (déjà calculé dans risk_study)
- fit_budget : part de la superficie disponible que le budget permet
  réellement de financer pour cette culture (0 à 1, plafonné à 1)

Les poids sont volontairement isolés ici pour être recalibrés facilement
par l'équipe sans toucher au reste du pipeline.
"""

from dataclasses import dataclass

# Poids par défaut — à ajuster selon les retours métier de l'équipe.
# Somme = 1 pour garder un score final entre 0 et 100.
POIDS_PROFIT = 0.45
POIDS_RISQUE = 0.30
POIDS_BUDGET_FIT = 0.25


@dataclass
class CandidatScoring:
    culture: str
    profit_net_par_ha: float
    risque_normalise: float
    superficie_max_financable_ha: float


@dataclass
class ScoreDetail:
    """Score final + toutes les composantes intermédiaires, pour l'explicabilité (bouton "Détails" côté frontend)."""
    score: float
    profit_normalise: float
    risque_normalise: float
    fit_budget: float


def _normaliser_min_max(valeurs: list[float]) -> list[float]:
    """Normalisation min-max classique ; gère le cas dégénéré (toutes égales)."""
    vmin, vmax = min(valeurs), max(valeurs)
    if vmax == vmin:
        return [1.0 for _ in valeurs]
    return [(v - vmin) / (vmax - vmin) for v in valeurs]


def calculer_matching_scores_detailles(
    candidats: list[CandidatScoring],
    superficie_disponible_ha: float,
) -> dict[str, ScoreDetail]:
    """
    Calcule le matching_score (0-100) pour chaque culture candidate, ainsi que
    les composantes normalisées ayant servi au calcul (utilisé pour la
    reconstitution du détail de calcul renvoyé au frontend).
    """
    profits = [c.profit_net_par_ha for c in candidats]
    profits_normalises = _normaliser_min_max(profits)

    details: dict[str, ScoreDetail] = {}

    for candidat, profit_norm in zip(candidats, profits_normalises):
        fit_budget = min(1.0, candidat.superficie_max_financable_ha / superficie_disponible_ha)

        score_brut = (
            POIDS_PROFIT * profit_norm
            + POIDS_RISQUE * (1 - candidat.risque_normalise)
            + POIDS_BUDGET_FIT * fit_budget
        )
        details[candidat.culture] = ScoreDetail(
            score=round(score_brut * 100, 2),
            profit_normalise=round(profit_norm, 4),
            risque_normalise=candidat.risque_normalise,
            fit_budget=round(fit_budget, 4),
        )

    return details


def calculer_matching_scores(
    candidats: list[CandidatScoring],
    superficie_disponible_ha: float,
) -> dict[str, float]:
    """Retourne uniquement {culture: score} — voir `calculer_matching_scores_detailles` pour le détail."""
    return {
        culture: detail.score
        for culture, detail in calculer_matching_scores_detailles(candidats, superficie_disponible_ha).items()
    }
