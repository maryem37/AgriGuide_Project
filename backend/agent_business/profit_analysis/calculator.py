"""
calculator.py
--------------
Pure, deterministic economic calculations for the farm profit-analysis report.

Design rule: NO LLM CALLS HERE. This module is the single source of truth for
every number in the final report. Groq/the LLM only ever receives these
already-computed numbers to narrate — it never does arithmetic itself. This
keeps the report auditable and reproducible.

All monetary inputs/outputs are in EUR, all yields in tonnes/hectare, all
areas in hectares, unless stated otherwise.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from enum import Enum
from typing import Optional


class RiskLevel(str, Enum):
    LOW = "Low"
    MEDIUM = "Medium"
    HIGH = "High"


class ConfidenceLevel(str, Enum):
    LOW = "Low"
    MEDIUM = "Medium"
    HIGH = "High"


@dataclass
class EconomicInputs:
    crop: str
    area_ha: float
    predicted_yield_t_per_ha: float          # from predictive model / FAO fallback
    price_per_ton: float                      # from RAG price retrieval (€/t)
    cost_per_ha: float                        # from RAG cost retrieval (€/ha), already
                                               # adjusted for irrigation + production method
    farmer_budget: Optional[float] = None     # what the farmer says they have available (€)

    # Optional data used for risk & confidence scoring
    yield_std_t_per_ha: Optional[float] = None       # historical yield volatility
    price_std_per_ton: Optional[float] = None        # historical price volatility
    n_yield_data_points: int = 0                      # how many years of yield history matched
    price_data_recency_years: Optional[int] = None    # how old is the newest matched price point
    exact_region_match: bool = True                   # did retrieval match the farmer's exact
                                                       # region, or fall back to a national average?


@dataclass
class EconomicReport:
    # Core required indicators
    gross_revenue: float
    estimated_total_cost: float
    estimated_profit: float
    budget_sufficiency: bool
    budget_gap: float  # positive = shortfall, negative/0 = surplus

    # Extra indicators
    profit_margin_pct: float
    roi_pct: float
    breakeven_price_per_ton: Optional[float]
    breakeven_yield_t_per_ha: Optional[float]
    risk_score: RiskLevel
    risk_reasons: list[str]
    confidence_score: ConfidenceLevel
    confidence_reasons: list[str]

    def to_dict(self) -> dict:
        return {
            "gross_revenue_eur": round(self.gross_revenue, 2),
            "estimated_total_cost_eur": round(self.estimated_total_cost, 2),
            "estimated_profit_eur": round(self.estimated_profit, 2),
            "profit_margin_pct": round(self.profit_margin_pct, 2),
            "roi_pct": round(self.roi_pct, 2),
            "breakeven_selling_price_eur_per_ton": (
                round(self.breakeven_price_per_ton, 2) if self.breakeven_price_per_ton is not None else None
            ),
            "breakeven_yield_t_per_ha": (
                round(self.breakeven_yield_t_per_ha, 3) if self.breakeven_yield_t_per_ha is not None else None
            ),
            "budget_sufficiency": "Yes" if self.budget_sufficiency else "No",
            "budget_gap_eur": round(self.budget_gap, 2),
            "risk_score": self.risk_score.value,
            "risk_reasons": self.risk_reasons,
            "confidence_score": self.confidence_score.value,
            "confidence_reasons": self.confidence_reasons,
        }


def _score_risk(
    inputs: EconomicInputs,
    profit_margin_pct: float,
    budget_sufficient: bool,
    total_yield_t: float = 0.0,
) -> tuple[RiskLevel, list[str]]:
    """
    Weighted composite risk score based on:
      - yield volatility (coefficient of variation)
      - price volatility (coefficient of variation)
      - thin/negative profit margin
      - budget insufficiency
    Each factor contributes 0-2 points; total maps to Low/Medium/High.
    """
    points = 0
    reasons = []

    if inputs.predicted_yield_t_per_ha <= 0:
        points += 3
        reasons.append("No usable yield estimate — crop/region likely not matched in historical data")

    if inputs.yield_std_t_per_ha is not None and inputs.predicted_yield_t_per_ha > 0:
        cv_yield = inputs.yield_std_t_per_ha / inputs.predicted_yield_t_per_ha
        if cv_yield > 0.25:
            points += 2
            reasons.append(f"High historical yield variability (CV={cv_yield:.0%})")
        elif cv_yield > 0.12:
            points += 1
            reasons.append(f"Moderate historical yield variability (CV={cv_yield:.0%})")

    if inputs.price_std_per_ton is not None and inputs.price_per_ton > 0:
        cv_price = inputs.price_std_per_ton / inputs.price_per_ton
        if cv_price > 0.20:
            points += 2
            reasons.append(f"High historical price volatility (CV={cv_price:.0%})")
        elif cv_price > 0.10:
            points += 1
            reasons.append(f"Moderate historical price volatility (CV={cv_price:.0%})")

    if profit_margin_pct < 0:
        points += 2
        reasons.append("Projected negative profit margin")
    elif profit_margin_pct < 10:
        points += 1
        reasons.append("Thin profit margin (<10%)")

    if not budget_sufficient:
        points += 1
        reasons.append("Stated budget is below estimated total cost")

    if points >= 5:
        level = RiskLevel.HIGH
    elif points >= 2:
        level = RiskLevel.MEDIUM
    else:
        level = RiskLevel.LOW

    if not reasons:
        reasons.append("No significant volatility or margin concerns detected in available data")

    return level, reasons


def _score_confidence(inputs: EconomicInputs) -> tuple[ConfidenceLevel, list[str]]:
    """
    Confidence reflects data quality behind the estimate, not the financial outcome itself.
    """
    points = 0
    reasons = []

    if inputs.n_yield_data_points >= 5:
        points += 2
        reasons.append(f"{inputs.n_yield_data_points} years of matched historical yield data")
    elif inputs.n_yield_data_points >= 2:
        points += 1
        reasons.append(f"Only {inputs.n_yield_data_points} years of matched historical yield data")
    else:
        reasons.append("Little or no historical yield data matched for this crop/region")

    if inputs.exact_region_match:
        points += 2
        reasons.append("Price/cost data matched to the exact region")
    else:
        reasons.append("Price/cost data fell back to a national average (region not matched)")

    if inputs.price_data_recency_years is not None:
        if inputs.price_data_recency_years <= 1:
            points += 2
            reasons.append("Price data is current (within the last year)")
        elif inputs.price_data_recency_years <= 3:
            points += 1
            reasons.append(f"Price data is {inputs.price_data_recency_years} years old")
        else:
            reasons.append(f"Price data is stale ({inputs.price_data_recency_years} years old)")

    if points >= 5:
        level = ConfidenceLevel.HIGH
    elif points >= 2:
        level = ConfidenceLevel.MEDIUM
    else:
        level = ConfidenceLevel.LOW

    return level, reasons


def compute_report(inputs: EconomicInputs) -> EconomicReport:
    """Runs all formulas and returns a fully populated EconomicReport."""

    if inputs.area_ha <= 0:
        raise ValueError("area_ha must be positive")
    if inputs.predicted_yield_t_per_ha < 0:
        raise ValueError("predicted_yield_t_per_ha cannot be negative")
    if inputs.price_per_ton < 0 or inputs.cost_per_ha < 0:
        raise ValueError("price_per_ton and cost_per_ha cannot be negative")

    total_yield_t = inputs.predicted_yield_t_per_ha * inputs.area_ha

    # --- Core indicators -----------------------------------------------
    gross_revenue = total_yield_t * inputs.price_per_ton
    estimated_total_cost = inputs.cost_per_ha * inputs.area_ha
    estimated_profit = gross_revenue - estimated_total_cost

    if inputs.farmer_budget is not None:
        budget_sufficient = inputs.farmer_budget >= estimated_total_cost
        budget_gap = estimated_total_cost - inputs.farmer_budget
    else:
        # No budget stated: treat as "not assessable" -> conservatively False, gap = full cost
        budget_sufficient = False
        budget_gap = estimated_total_cost

    # --- Extra indicators ------------------------------------------------
    if gross_revenue > 0:
        profit_margin_pct = estimated_profit / gross_revenue * 100
    else:
        # Zero revenue is not "0% margin" (break-even) — it's undefined/total
        # loss. Flag it clearly rather than showing a misleadingly benign 0.0%.
        profit_margin_pct = -100.0

    roi_pct = (estimated_profit / estimated_total_cost * 100) if estimated_total_cost > 0 else 0.0

    breakeven_price_per_ton = (estimated_total_cost / total_yield_t) if total_yield_t > 0 else None
    breakeven_yield_t_per_ha = (
        estimated_total_cost / (inputs.price_per_ton * inputs.area_ha)
        if inputs.price_per_ton > 0 and inputs.area_ha > 0
        else None
    )

    risk_score, risk_reasons = _score_risk(inputs, profit_margin_pct, budget_sufficient, total_yield_t)
    confidence_score, confidence_reasons = _score_confidence(inputs)

    return EconomicReport(
        gross_revenue=gross_revenue,
        estimated_total_cost=estimated_total_cost,
        estimated_profit=estimated_profit,
        budget_sufficiency=budget_sufficient,
        budget_gap=budget_gap,
        profit_margin_pct=profit_margin_pct,
        roi_pct=roi_pct,
        breakeven_price_per_ton=breakeven_price_per_ton,
        breakeven_yield_t_per_ha=breakeven_yield_t_per_ha,
        risk_score=risk_score,
        risk_reasons=risk_reasons,
        confidence_score=confidence_score,
        confidence_reasons=confidence_reasons,
    )


# --------------------------------------------------------------------------- #
# Self-test
# --------------------------------------------------------------------------- #

if __name__ == "__main__":
    # Example: 10 ha of wheat, 6 t/ha yield, sold at 220 €/t, cost 900 €/ha, budget 8000€
    inputs = EconomicInputs(
        crop="Blé tendre",
        area_ha=10,
        predicted_yield_t_per_ha=6.0,
        price_per_ton=220.0,
        cost_per_ha=900.0,
        farmer_budget=8000.0,
        yield_std_t_per_ha=0.9,
        price_std_per_ton=15.0,
        n_yield_data_points=6,
        price_data_recency_years=0,
        exact_region_match=True,
    )
    report = compute_report(inputs)
    import json
    print(json.dumps(report.to_dict(), indent=2, ensure_ascii=False))

    # Sanity checks
    assert report.gross_revenue == 6.0 * 10 * 220.0
    assert report.estimated_total_cost == 900.0 * 10
    assert report.estimated_profit == report.gross_revenue - report.estimated_total_cost
    # budget (8000) < cost (9000) -> insufficient, gap = 1000
    assert report.budget_sufficiency is False
    assert round(report.budget_gap, 2) == 1000.0
    print("\nAll self-tests passed.")