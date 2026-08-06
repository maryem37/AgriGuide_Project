"""
Fertilizer (nitrogen dose) and irrigation-need estimates for a given
crop. Deliberately NOT LLM-generated — a wrong dose or irrigation
volume is a real agronomic/financial mistake, not just a wrong
sentence, so this uses published reference formulas and constants in
plain Python, same trust tier as ml_service.py's scoring.

Ported as-is from the standalone `agri-advisor-parcelle` prototype.

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

  Exception — legumes (soja, pois protéagineux): this yield-scaling
  formula does not apply to them at all. Both fix their own
  atmospheric nitrogen via rhizobia and need little to no synthetic N;
  running the normal besoins = yield_obj * b_n_kg_per_q formula on them
  would be actively wrong (it would recommend real fertilizer N for a
  crop that mostly doesn't need it, and can specifically be misleading
  for pois, where synthetic N is banned in nitrate-vulnerable zones).
  These two use `_LEGUME_STARTER_N_KG_HA` instead — a small flat
  starter dose, independent of yield objective, with an explanatory
  note.

- Irrigation: FAO-56's crop water balance
  (need = ET0 x Kc - effective rainfall), using a single representative
  mid-season Kc per crop rather than a full growth-stage curve (we
  don't know planting date / current growth stage for a parcel), and
  Open-Meteo's 16-day forecast window rather than a full season.

Every numeric constant below is a published reference value used for
illustration at this project's scope, not a calibrated agronomic
threshold — same rigor level as ml_service.py's crop tolerance ranges.
"""
from app.models.schemas import SoilData, WeatherData, AgroCalcEstimate, DLCropObservation
from app.services.yield_service import BASE_YIELD_Q_HA

# kg N needed per quintal (100kg) of harvested yield — COMIFER/Arvalis
# reference order-of-magnitude values. The yield objective itself
# (previously a "default_yield_q_ha" duplicated inline here) now comes
# from yield_service.BASE_YIELD_Q_HA — same French-average reference
# values, single source of truth — used only as a fallback when the
# caller doesn't supply a real, parcel-specific yield objective (main.py
# now always does, via yield_service.estimate_yield()).
#
# Potato and sugar beet coefficients are deliberately small relative to
# their huge fresh-weight yield objective (~420 and ~850 q/ha) — total
# N need per hectare is what's agronomically realistic (potato
# ~150-180 kg N/ha, sugar beet ~100-140 kg N/ha), not what the raw
# quintal count might suggest.
_N_CONSTANTS = {
    "ble_tendre": {"b_n_kg_per_q": 3.0},
    "mais":       {"b_n_kg_per_q": 2.2},
    "colza":      {"b_n_kg_per_q": 7.0},
    "orge":       {"b_n_kg_per_q": 2.6},
    "tournesol":  {"b_n_kg_per_q": 4.5},
    "pomme_de_terre": {"b_n_kg_per_q": 0.4},
    "betterave_sucriere": {"b_n_kg_per_q": 0.14},
}

# Legumes: fix their own atmospheric N via rhizobia. Skip the yield-
# scaling formula entirely and use a small flat starter dose instead.
# Pois: typically no synthetic N at all in real French guidance (and
# banned outright in nitrate-vulnerable zones) — 0 kg N/ha. Soja:
# occasionally given a very light starter dose if inoculation/nodulation
# is uncertain — kept small and clearly labeled as optional-in-practice.
_LEGUME_STARTER_N_KG_HA = {
    "soja": 20.0,
    "pois_proteagineux": 0.0,
}

_CAU = 0.7  # apparent utilization coefficient — typical published value for mineral N fertilizer

# --- DL grassland-conversion N credit (Phase B integration) -----------------
# Published, well-documented agronomic effect ("arrière-effet prairie" /
# grassland plow-down effect): converting permanent or temporary meadow to
# arable land releases meadow-accumulated organic N via mineralization for
# roughly 1-2 following seasons, on top of the parcel's normal organic-carbon
# supply. dl_service.py's TempCNN classifier is the only source in this
# pipeline that can tell us the parcel is CURRENTLY under meadow — a
# genuinely useful, real-world signal for what it actually observes (current
# land cover), unlike using it as a suitability/yield signal (which the
# rest of this project deliberately avoids — see yield_service.py).
# Credit values are illustrative COMIFER-ballpark figures (permanent meadow
# accumulates more organic N over time than a short temporary rotation),
# same "documented approximation, not a real Nmin test" rigor as
# _estimate_soil_n_supply below.
_DL_PRAIRIE_N_CREDIT_KG_HA = {
    "permanent meadows": 40.0,
    "temporary meadows": 25.0,
}
_DL_MIN_CONFIDENCE_FOR_CREDIT = 0.5
_DL_MIN_TIMESTEPS_FOR_CREDIT = 5


def _dl_prairie_n_credit(dl_observation: "DLCropObservation | None") -> tuple[float, str | None]:
    """Returns (credit_kg_ha, note). Credit is 0 / note is None unless the DL
    classifier confidently observes the parcel as currently under meadow —
    exactly the same confidence/timestep gate as ml_service.py's evidence
    bonus, so both integrations degrade identically when the classifier is
    unavailable or unsure."""
    if dl_observation is None or dl_observation.source == "unavailable":
        return 0.0, None
    if dl_observation.confidence is None or dl_observation.confidence < _DL_MIN_CONFIDENCE_FOR_CREDIT:
        return 0.0, None
    if (dl_observation.observation_timesteps or 0) < _DL_MIN_TIMESTEPS_FOR_CREDIT:
        return 0.0, None
    credit = _DL_PRAIRIE_N_CREDIT_KG_HA.get(dl_observation.predicted_class_en or "")
    if not credit:
        return 0.0, None
    note = (
        f"Crédit azote de {credit} kg N/ha appliqué : le classifieur DL (TempCNN/BreizhCrops) "
        f"observe cette parcelle actuellement en {dl_observation.predicted_class_fr} "
        f"(confiance {round(dl_observation.confidence * 100)}%) — le retournement de prairie "
        f"libère de l'azote organique minéralisé pendant 1-2 saisons (repère COMIFER), en plus "
        f"de la fourniture du sol estimée ci-dessous. Approximation documentée, ne remplace pas "
        f"un diagnostic agronomique de retournement réel."
    )
    return credit, note

# Realistic regulatory-ballpark N dose ceilings, kg N/ha — French nitrate-
# vulnerable-zone reference doses cap total N application regardless of
# what a yield-based formula predicts. Added after yield_service.py made
# yield_objective_q_ha parcel-specific (previously always the fixed
# default): the linear besoins = yield_obj * b_n_kg_per_q formula, only
# ever calibrated/verified at the default 75 q/ha wheat objective, was
# found to produce 334 kg N/ha for a high-suitability parcel with a
# ~105 q/ha objective — well past real ceilings. Capping here, not by
# artificially shrinking yield_objective_q_ha, keeps the yield estimate
# itself honest while keeping the fertilizer dose realistic.
#
# Sugar beet's ceiling is much lower than its huge yield objective would
# suggest — real French guidance caps sugar beet N well below cereal
# levels despite the much bigger harvest. Legume ceilings exist only as
# a safety backstop (their starter dose never approaches them).
_MAX_REALISTIC_DOSE_KG_HA = {
    "ble_tendre": 220,
    "mais": 220,
    "colza": 220,
    "orge": 180,
    "tournesol": 120,
    "pomme_de_terre": 220,
    "betterave_sucriere": 160,
    "soja": 50,
    "pois_proteagineux": 30,
}

# FAO-56 mid-season crop coefficients (Kc) — approximate reference
# values, not a full growth-stage curve.
_KC_MID = {
    "ble_tendre": 1.15,
    "mais": 1.20,
    "colza": 1.10,
    "orge": 1.10,
    "tournesol": 1.10,
    "pomme_de_terre": 1.15,
    "betterave_sucriere": 1.20,
    "soja": 1.15,
    "pois_proteagineux": 1.05,
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


def _estimate_legume_nitrogen(crop: str, starter_dose: float) -> dict:
    """Legume branch — bypasses the yield-scaling COMIFER-style formula
    entirely. Returns the same dict shape as estimate_nitrogen() so
    callers don't need to special-case it."""
    if starter_dose <= 0:
        note = (
            f"{crop.replace('_', ' ').capitalize()} est une légumineuse : elle fixe son propre "
            f"azote atmosphérique via les rhizobiums et n'a normalement besoin d'aucun apport "
            f"d'azote de synthèse. Aucune dose n'est recommandée ici (et l'azote de synthèse est "
            f"interdit pour le pois protéagineux en zone vulnérable aux nitrates)."
        )
    else:
        note = (
            f"{crop.replace('_', ' ').capitalize()} est une légumineuse : elle fixe son propre "
            f"azote atmosphérique via les rhizobiums et n'a besoin que d'une dose de démarrage "
            f"limitée ({starter_dose} kg N/ha), utile surtout en cas d'incertitude sur la "
            f"nodulation — pas un apport calculé sur objectif de rendement comme pour les "
            f"cultures non-légumineuses."
        )
    return {
        "n_dose_kg_ha": starter_dose,
        "n_besoins_kg_ha": None,
        "n_fournitures_kg_ha": None,
        "yield_objective_q_ha": None,
        "n_method_note": note,
    }


def estimate_nitrogen(
    crop: str,
    soil: SoilData,
    yield_objective_q_ha: float | None = None,
    dl_observation: "DLCropObservation | None" = None,
) -> dict:
    """Returns dose_kg_ha, besoins_kg_ha, fournitures_kg_ha, dl_credit_kg_ha, yield_objective_q_ha, note, warning."""
    if crop in _LEGUME_STARTER_N_KG_HA:
        return _estimate_legume_nitrogen(crop, _LEGUME_STARTER_N_KG_HA[crop])

    consts = _N_CONSTANTS.get(crop)
    if consts is None:
        return {"warning": f"Aucune constante azote disponible pour la culture '{crop}'."}

    yield_obj = yield_objective_q_ha or BASE_YIELD_Q_HA.get(crop)
    if yield_obj is None:
        return {"warning": f"Aucun objectif de rendement disponible (ni fourni, ni référence) pour la culture '{crop}'."}
    besoins = round(yield_obj * consts["b_n_kg_per_q"], 1)
    fournitures, supply_note = _estimate_soil_n_supply(soil)
    dl_credit, dl_note = _dl_prairie_n_credit(dl_observation)
    dose = max(0.0, round((besoins - fournitures - dl_credit) / _CAU, 1))

    ceiling = _MAX_REALISTIC_DOSE_KG_HA.get(crop)
    cap_note = ""
    if ceiling is not None and dose > ceiling:
        dose = ceiling
        cap_note = (
            f" Dose plafonnée à {ceiling} kg N/ha (repère réglementaire zone vulnérable "
            f"nitrates) — le calcul brut dépassait ce plafond pour l'objectif de rendement donné."
        )

    yield_note = (
        f"Objectif de rendement par défaut ({yield_obj} q/ha, moyenne française indicative)."
        if not yield_objective_q_ha
        else f"Objectif de rendement fourni : {yield_obj} q/ha."
    )

    note_parts = [yield_note, supply_note]
    if dl_note:
        note_parts.append(dl_note)
    note = " ".join(note_parts) + cap_note

    return {
        "n_dose_kg_ha": dose,
        "n_besoins_kg_ha": besoins,
        "n_fournitures_kg_ha": fournitures,
        "n_dl_credit_kg_ha": dl_credit,
        "yield_objective_q_ha": yield_obj,
        "n_method_note": note,
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
    crop: str,
    soil: SoilData,
    weather: WeatherData,
    yield_objective_q_ha: float | None = None,
    dl_observation: "DLCropObservation | None" = None,
) -> AgroCalcEstimate:
    n_result = estimate_nitrogen(crop, soil, yield_objective_q_ha, dl_observation)
    irr_result = estimate_irrigation(crop, weather)

    warnings = [w for w in (n_result.get("warning"), irr_result.get("warning")) if w]

    return AgroCalcEstimate(
        crop=crop,
        n_dose_kg_ha=n_result.get("n_dose_kg_ha"),
        n_besoins_kg_ha=n_result.get("n_besoins_kg_ha"),
        n_fournitures_kg_ha=n_result.get("n_fournitures_kg_ha"),
        n_dl_credit_kg_ha=n_result.get("n_dl_credit_kg_ha"),
        yield_objective_q_ha=n_result.get("yield_objective_q_ha"),
        n_method_note=n_result.get("n_method_note"),
        irrigation_need_mm=irr_result.get("irrigation_need_mm"),
        irrigation_window_days=irr_result.get("irrigation_window_days"),
        total_et0_mm=irr_result.get("total_et0_mm"),
        total_effective_precip_mm=irr_result.get("total_effective_precip_mm"),
        irrigation_method_note=irr_result.get("irrigation_method_note"),
        warning=" ".join(warnings) if warnings else None,
    )
