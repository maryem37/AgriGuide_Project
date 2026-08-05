"""
Deterministic yield estimate for the top-recommended crop.

Same trust tier as ml_service.py's scoring and agro_calc_service.py's
fertilizer/irrigation formulas: no real historical yield-trial data,
soil-yield curves, or crop management/genotype info exists at this
project's scope, so a genuinely calibrated yield model isn't possible
— this is an honest, labeled placeholder, not a hidden one.

Ported as-is from the standalone `agri-advisor-parcelle` prototype.

    yield_estimate_q_ha = base_yield_q_ha(crop) x adjustment_factor(score)

- base_yield_q_ha: published French national-average yield per crop
  (Agreste-ballpark). This is the SAME reference value
  agro_calc_service.py already used as its fertilizer yield-objective
  default — moved here as the single source of truth (BASE_YIELD_Q_HA)
  so the two services can't silently drift apart; agro_calc_service.py
  imports it instead of keeping its own copy.

- adjustment_factor: linear rescale of ml_service.py's 0-1 crop
  suitability score into a bounded yield multiplier:
      factor = 0.6 + 0.8 * suitability_score  ->  range [0.6, 1.4]
  i.e. a poor-fit parcel (score 0) yields ~60% of the national average;
  an excellent-fit parcel (score 1) yields ~140%. Sanity-checked against
  real French yield spreads (see check_yield.py in the prototype):
  ble_tendre 45-105, mais 57-133, colza 21-49, orge 42-98,
  tournesol 16.8-39.2 q/ha — all within real published poor-to-excellent
  French yield ranges, not the runaway values an uncapped or
  wrongly-scaled formula would produce (the same class of bug the
  fertilizer dose calibration caught: an unrealistic 275 kg N/ha vs
  real guidance of ~180-220).

- No separate precipitation/weather-stress multiplier: the suitability
  score already includes a precipitation factor (ml_service.py's
  precip_score) — adding a second weather-based adjustment here would
  double-count the same signal, same error class as the independently-
  recomputed weather mean bug found in synthesis_service.py.

- Deliberately does NOT use NDVI: synthesis_service.py's Stage 1 prompt
  explicitly forbids treating NDVI as a suitability signal (it reflects
  CURRENT ground conditions at the time of the satellite pass — bare
  soil, an unrelated prior crop, weeds on fallow land — not a
  forward-looking yield signal for a crop that may not even be planted
  yet). Using it here would silently contradict that documented
  decision.

- Deliberately does NOT use the DL classifier: dl_service.py's output
  is a descriptive land-cover observation, never fed into any
  scoring/estimation path anywhere in the pipeline (see schemas.py's
  DLCropObservation docstring) — kept consistent with that rule.

- Crop-pool expansion (potato, sugar beet, soybean, field pea):
  base_yield_q_ha values are French national-average references,
  Agreste-ballpark, same sourcing tier as the original 5. Note the
  scale difference is large but structurally harmless — potato and
  sugar beet are simply reported in much bigger fresh-weight numbers
  (t/ha-equivalent) than a cereal; the factor math is unchanged and
  was re-sanity-checked at these magnitudes in check_yield.py.

yield_range_low/high_q_ha is a fixed +-15% band representing THIS
METHOD's uncertainty (a rule-based rescale, not a statistical
prediction interval) — stated as such in method_note.
"""
from app.models.schemas import CropRecommendation, YieldEstimate

# Published French national-average yields (Agreste-ballpark), q/ha.
# Single source of truth — agro_calc_service.py imports this rather
# than keeping its own copy (previously duplicated inline, a drift risk).
BASE_YIELD_Q_HA = {
    "ble_tendre": 75,
    "mais": 95,
    "colza": 35,
    "orge": 70,
    "tournesol": 28,
    # --- Crop-pool expansion ---
    "pomme_de_terre": 420,      # ~42 t/ha French average, fresh weight
    "betterave_sucriere": 850,  # ~85 t/ha French average, fresh weight
    "soja": 28,
    "pois_proteagineux": 40,
}

_FACTOR_FLOOR = 0.6
_FACTOR_SPAN = 0.8   # factor = _FACTOR_FLOOR + _FACTOR_SPAN * score -> [0.6, 1.4]
_UNCERTAINTY_BAND = 0.15  # +-15% method-uncertainty band, not a statistical CI


def estimate_yield(rec: CropRecommendation) -> YieldEstimate:
    """Takes the top CropRecommendation from ml_service.recommend_crops()
    (needs both suitability_score and crop) and returns a YieldEstimate."""
    base = BASE_YIELD_Q_HA.get(rec.crop)
    if base is None:
        return YieldEstimate(
            crop=rec.crop,
            warning=f"Aucun rendement de référence disponible pour la culture '{rec.crop}'.",
        )

    factor = round(_FACTOR_FLOOR + _FACTOR_SPAN * rec.suitability_score, 3)
    point = round(base * factor, 1)
    low = round(point * (1 - _UNCERTAINTY_BAND), 1)
    high = round(point * (1 + _UNCERTAINTY_BAND), 1)

    return YieldEstimate(
        crop=rec.crop,
        yield_estimate_q_ha=point,
        yield_range_low_q_ha=low,
        yield_range_high_q_ha=high,
        base_yield_q_ha=base,
        suitability_score=rec.suitability_score,
        adjustment_factor=factor,
        method_note=(
            f"Estimation simplifiée : moyenne nationale française indicative "
            f"({base} q/ha) multipliée par le score d'adéquation de la parcelle "
            f"({round(rec.suitability_score * 100)}%, facteur {factor}). Ne remplace pas un "
            f"modèle de rendement calibré sur données historiques réelles — la fourchette de "
            f"±15% reflète l'incertitude de cette méthode, pas un intervalle de confiance "
            f"statistique."
        ),
    )
