"""
Fertilizer (nitrogen dose) and irrigation-need estimates for the
top-recommended crop. Deliberately NOT LLM-generated — a wrong dose or
irrigation volume is a real agronomic/financial mistake, not just a
wrong sentence, so this uses published reference formulas and
constants in plain Python, same trust tier as ml_service.py's scoring.

Both methods here are honest simplifications of real French/FAO
agronomic methods, not the full versions:

- Nitrogen: a simplified COMIFER-style balance sheet
  (dose = (besoins - fournitures) / CAU). The real COMIFER method
  requires an actual Nmin soil test and previous-crop history, neither
  of which this project has access to. "Fournitures" here is
  estimated from SoilGrids' organic carbon content via a broad,
  labeled approximation — NOT a substitute for a real Nmin test.
  Yield objective defaults to a typical French average per crop
  (Agreste-ballpark) and can be overridden by the caller.

- Irrigation: FAO-56's crop water balance
  (need = ET0 x Kc - effective rainfall), using a single representative
  mid-season Kc per crop rather than a full growth-stage curve (we
  don't know planting date / current growth stage for a parcel), and
  Open-Meteo's 16-day forecast window rather than a full season.

Every numeric constant below is a published reference value used for
illustration at this project's scope, not a calibrated agronomic
threshold — same rigor level as ml_service.py's crop tolerance ranges.
"""
from schemas import SoilData, WeatherData, AgroCalcEstimate

# kg N needed per quintal (100kg) of harvested yield — COMIFER/Arvalis
# reference order-of-magnitude values.
# default_yield_q_ha — typical French average yield (Agreste ballpark),
# used only when the caller doesn't supply a real yield objective.
_N_CONSTANTS = {
    "ble_tendre": {"b_n_kg_per_q": 3.0, "default_yield_q_ha": 75},
    "mais":       {"b_n_kg_per_q": 2.2, "default_yield_q_ha": 95},
    "colza":      {"b_n_kg_per_q": 7.0, "default_yield_q_ha": 35},
    "orge":       {"b_n_kg_per_q": 2.6, "default_yield_q_ha": 70},
    "tournesol":  {"b_n_kg_per_q": 4.5, "default_yield_q_ha": 28},
}

_CAU = 0.7  # apparent utilization coefficient — typical published value for mineral N fertilizer

# FAO-56 mid-season crop coefficients (Kc) — approximate reference
# values, not a full growth-stage curve.
_KC_MID = {
    "ble_tendre": 1.15,
    "mais": 1.20,
    "colza": 1.10,
    "orge": 1.10,
    "tournesol": 1.10,
}

_RAIN_EFFECTIVENESS = 0.8  # simple fixed factor — real methods (e.g. USDA SCS) are more complex, out of scope here


def _estimate_soil_n_supply(soil: SoilData) -> tuple[float, str]:
    """
    Rough "fournitures du sol" proxy from organic carbon, interpolated
    between 50 kg N/ha (low organic matter) and 110 kg N/ha (high organic
    matter) over a 10-30 g/kg typical range — calibrated so a mid-range
    input produces a dose in the ballpark of real French guidance (a
    75 q/ha wheat objective should land near 180-220 kg N/ha total, not
    the ~275 kg N/ha an earlier, too-low 20-50 kg N/ha range produced).
    This is NOT a real mineralization/Nmin measurement — it's a labeled
    approximation standing in for one, same honesty pattern as the rest
    of this project's placeholder scoring.
    """
    if soil.organic_carbon_g_kg is None:
        return 70.0, "Aucune donnée de carbone organique — valeur par défaut utilisée (approximation, pas un test de sol réel)."
    oc = max(10.0, min(30.0, soil.organic_carbon_g_kg))
    supply = 50.0 + (oc - 10.0) / 20.0 * 60.0
    return round(supply, 1), "Estimée à partir du carbone organique du sol (SoilGrids) — approximation, ne remplace pas une analyse de sol réelle (reliquat azoté)."


def estimate_nitrogen(crop: str, soil: SoilData, yield_objective_q_ha: float | None = None) -> dict:
    """Returns dose_kg_ha, besoins_kg_ha, fournitures_kg_ha, yield_objective_q_ha, note, warning."""
    consts = _N_CONSTANTS.get(crop)
    if consts is None:
        return {"warning": f"Aucune constante azote disponible pour la culture '{crop}'."}

    yield_obj = yield_objective_q_ha or consts["default_yield_q_ha"]
    besoins = round(yield_obj * consts["b_n_kg_per_q"], 1)
    fournitures, supply_note = _estimate_soil_n_supply(soil)
    dose = max(0.0, round((besoins - fournitures) / _CAU, 1))

    yield_note = (
        f"Objectif de rendement par défaut ({yield_obj} q/ha, moyenne française indicative)."
        if not yield_objective_q_ha
        else f"Objectif de rendement fourni : {yield_obj} q/ha."
    )

    return {
        "n_dose_kg_ha": dose,
        "n_besoins_kg_ha": besoins,
        "n_fournitures_kg_ha": fournitures,
        "yield_objective_q_ha": yield_obj,
        "n_method_note": f"{yield_note} {supply_note}",
    }


def estimate_irrigation(crop: str, weather: WeatherData) -> dict:
    """Returns irrigation_need_mm, window_days, total_et0_mm, total_effective_precip_mm, note, warning."""
    kc = _KC_MID.get(crop)
    if kc is None:
        return {"warning": f"Aucun coefficient cultural (Kc) disponible pour la culture '{crop}'."}

    et0 = [v for v in (weather.daily_et0_mm or []) if v is not None]
    precip = [v for v in (weather.daily_precip_mm or []) if v is not None]
    if not et0:
        return {"warning": "Données ET0 (évapotranspiration) indisponibles — impossible d'estimer le besoin d'irrigation."}

    total_et0 = sum(et0)
    total_precip = sum(precip) if precip else 0.0
    effective_precip = total_precip * _RAIN_EFFECTIVENESS
    etc = total_et0 * kc
    need = max(0.0, round(etc - effective_precip, 1))

    return {
        "irrigation_need_mm": need,
        "irrigation_window_days": len(et0),
        "total_et0_mm": round(total_et0, 1),
        "total_effective_precip_mm": round(effective_precip, 1),
        "irrigation_method_note": (
            f"Estimation FAO-56 (ETc = ET0 x Kc, Kc={kc} valeur médiane de saison, pas de courbe de "
            f"stade phénologique) sur la fenêtre de prévision Open-Meteo ({len(et0)} jours) uniquement "
            f"— pas un bilan hydrique de saison complète."
        ),
    }


def estimate_fertilizer_and_irrigation(
    crop: str, soil: SoilData, weather: WeatherData, yield_objective_q_ha: float | None = None
) -> AgroCalcEstimate:
    n_result = estimate_nitrogen(crop, soil, yield_objective_q_ha)
    irr_result = estimate_irrigation(crop, weather)

    warnings = [w for w in (n_result.get("warning"), irr_result.get("warning")) if w]

    return AgroCalcEstimate(
        crop=crop,
        n_dose_kg_ha=n_result.get("n_dose_kg_ha"),
        n_besoins_kg_ha=n_result.get("n_besoins_kg_ha"),
        n_fournitures_kg_ha=n_result.get("n_fournitures_kg_ha"),
        yield_objective_q_ha=n_result.get("yield_objective_q_ha"),
        n_method_note=n_result.get("n_method_note"),
        irrigation_need_mm=irr_result.get("irrigation_need_mm"),
        irrigation_window_days=irr_result.get("irrigation_window_days"),
        total_et0_mm=irr_result.get("total_et0_mm"),
        total_effective_precip_mm=irr_result.get("total_effective_precip_mm"),
        irrigation_method_note=irr_result.get("irrigation_method_note"),
        warning=" ".join(warnings) if warnings else None,
    )
