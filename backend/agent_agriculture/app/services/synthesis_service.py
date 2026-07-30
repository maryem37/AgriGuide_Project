"""
Two-stage generation. Stage 1 builds a grounded structured JSON (every
claim tagged with a source chunk or dropped). Stage 2 turns that JSON
into the French report. Kept as two separate Mistral calls, not one —
collapsing them loses the traceability guarantee.

Ported as-is from the standalone `agri-advisor-parcelle` prototype.

Three-layer grounding defense against invented figures:
  1. source_chunk_id validation — drop any claim citing a chunk ID that
     wasn't actually retrieved.
  2. Stage 2 prompt explicitly forbids introducing numbers not present
     in the JSON payload, WITH a carve-out for score formatting (score
     * 100 is arithmetic on a real number, not invention).
  3. Post-generation numeric audit — cross-checks every number in the
     final report against the source data, flags anything unverifiable.
None of these make invention impossible, but together they make it
visible instead of silently trusted.
"""
import asyncio
import json
import re
from mistralai import Mistral
from app.config import settings
from app.models.schemas import (
    ParcelResolution, SoilData, WeatherData, CropRecommendation,
    RetrievedChunk, SynthesisJSON, AdvisorReport, VegetationData, DLCropObservation, AgroCalcEstimate,
)

_client = Mistral(api_key=settings.mistral_api_key) if settings.mistral_api_key else None


def compute_weather_stats(weather: WeatherData) -> dict:
    """
    Authoritative weather aggregates, computed in Python — NOT by the LLM.
    Filters None (trailing forecast days Open-Meteo sometimes returns null
    for), same as ml_service.py. Exposed (not prefixed) since the router
    also uses it to fill `AnalyzeResponse.weather_stats`.
    """
    temps = [t for t in (weather.daily_temp_mean_c or []) if t is not None]
    precip = [p for p in (weather.daily_precip_mm or []) if p is not None]
    stats = {}
    if temps:
        stats["mean_temp_c"] = round(sum(temps) / len(temps), 2)
        stats["min_temp_c"] = round(min(temps), 2)
        stats["max_temp_c"] = round(max(temps), 2)
    if precip:
        stats["total_precip_mm"] = round(sum(precip), 2)
        stats["rainy_days_count"] = sum(1 for p in precip if p > 0.1)
    return stats


_STAGE1_SYSTEM = """You are an agronomy data synthesis assistant.
You will be given raw soil data, weather data, vegetation (satellite
NDVI) data, crop suitability scores, and retrieved document chunks —
for context only. Your job is ONLY to extract grounded claims from the
retrieved chunks and note data gaps. Do NOT summarize or restate the
soil/weather/vegetation data yourself — that is handled directly from
the real data afterward, not from anything you write here.

Your output MUST match this exact shape:
{
  "grounded_claims": [
    {"claim": "<text>", "source_chunk_id": "<EXACT chunk_id from the provided chunks>"}
  ],
  "data_gaps": [
    "<plain text description of the gap>"
  ]
}

Rules:
- data_gaps MUST be an array of plain strings, NOT objects.
- Every entry in grounded_claims MUST use a source_chunk_id that is an
  EXACT, VERBATIM copy of a chunk_id from the retrieved_chunks list you
  were given. Do not invent, abbreviate, or paraphrase a chunk_id. If
  you cannot cite a real chunk_id for a claim, DO NOT include the claim.
- Any specific number (a dosage, a rate like kg/ha or mm/week, a
  threshold) that you state as a recommendation MUST appear in either
  the provided soil/weather data OR the text of a cited chunk. Do not
  state a number from general agronomic knowledge and label it as
  grounded — only include it if it is traceable to the data you were
  actually given.
- NDVI (vegetation data) describes CURRENT ground conditions only — a
  snapshot/short-window average, not a crop suitability signal. Do not
  cite it as grounds for a claim or crop recommendation.
- If data is missing, describe it as a plain-string entry in data_gaps
  instead of guessing or estimating a number to fill the gap.
Return ONLY valid JSON matching the schema above, nothing else."""

_STAGE2_SYSTEM = """You are writing a farmer-facing report in French.
You may ONLY use information present in the structured JSON you are given.

STRUCTURE — use EXACTLY this markdown format, with real "## " (two
hashes) headings for every top-level section, so the report can be
parsed programmatically:

## Résumé de la parcelle
Include the parcel's land area (from parcel.area_ha in the JSON — state
it as "X.XX hectares"; if area_ha is null, say the area is unavailable)
and its declared crop if present.

## Sol
State soil properties as a bulleted list, one property per line,
formatted "- **Nom** : valeur (unité)". You MUST include the nitrogen
rate (soil.nitrogen_g_kg) as one of these bullets if it is present in
the JSON, labeled "Azote".

## Météo
weather_summary now contains the RAW daily lists (daily_temp_mean_c,
daily_precip_mm, daily_dates) — do not try to bullet-list 16 raw daily
values. Instead, report the AGGREGATE figures from weather_stats
(mean_temp_c, min_temp_c, max_temp_c, total_precip_mm,
rainy_days_count) as a bulleted list, formatted "- **Nom** : valeur
(unité)", using weather_stats' values exactly as given — these are
already correctly computed, do not recompute or adjust them. Also
state weather_summary.source. If weather_stats is empty (no valid
daily data), say weather data could not be summarized instead of
inventing aggregate figures.

## Végétation
State vegetation_summary fields the same bulleted way (e.g. "- **NDVI
moyen** : valeur"). NDVI reflects what's currently on the ground right
now (bare soil, growing crop, weeds on fallow land) over the
observation window — it is descriptive context, NOT a signal used to
choose a recommended crop. Say so briefly. If vegetation_summary.source
is "unavailable", vegetation_summary.mean_ndvi WILL be null — in that
case state plainly that satellite data could not be retrieved for this
parcel, and do NOT state any NDVI number (there isn't one to report;
inventing a plausible-looking value here is exactly the kind of
fabrication this report must never produce).

If dl_observation_summary.source is "dl-tempcnn-breizhcrops", add one
more bullet in this same section: "- **Culture observée par satellite
(IA)** : {predicted_class_fr} (confiance : {confidence * 100, rounded}%)".
The confidence percentage is confidence multiplied by 100 — arithmetic
on a real number already in the JSON, not an invented figure, same as
the crop-score percentage below. This is a separate, independent
observation from NDVI and from the RPG-declared crop — do not treat it
as a recommendation and do not blend it with NDVI's description. If
dl_observation_summary.source is "unavailable", omit this bullet
entirely rather than mentioning a satellite AI observation that
doesn't exist.

## Cultures recommandées
For EACH crop in crop_recommendations, output one block in this exact
form:
### <rank>. <crop name>
**Score : <suitability_score * 100, rounded to nearest whole number>%**
<one sentence reasoning tied to the crop's reasoning_features>
The percentage MUST be suitability_score multiplied by 100 — this is
arithmetic on a real number already in your data, not an invented
figure, so compute it precisely; do not write "0%" as a placeholder.

## Fertilisation et irrigation
Only include this section if agro_calc_summary.warning is null or if
at least one of n_dose_kg_ha / irrigation_need_mm is present — if both
are null AND a warning is present, state the warning plainly instead
of the section content.

If n_dose_kg_ha is present, state it as "- **Dose d'azote estimée** :
{n_dose_kg_ha} kg N/ha" followed immediately by n_method_note verbatim
(do not reword it — it already states its own approximation caveat
precisely).

If irrigation_need_mm is present, state it as "- **Besoin d'irrigation
estimé ({irrigation_window_days} jours)** : {irrigation_need_mm} mm"
followed immediately by irrigation_method_note verbatim.

Every number in this section comes directly from agro_calc_summary —
do not recompute, round differently, or adjust any of them. This
section is a simplified estimate, not a substitute for a real soil
test or a full agronomic study — say so in one short sentence at the
end of the section, in addition to (not instead of) the two method
notes above.

## Conseils pratiques
Bulleted advice grounded in grounded_claims, citing the source document
per claim, e.g. "(Source: {source_document})".

## Alertes
Risks and things to watch, grounded in the data provided. If
dl_mismatch_note is present (not null) in the JSON, include it as its
own bullet point, copied verbatim — do not paraphrase, reword, or
recompute any figure inside it; it was already written and verified
outside this generation step.

## Données manquantes
Restate data_gaps as a bulleted list.

STRICT RULE ON NUMBERS: other than the crop score calculation described
above, you may not introduce any number, percentage, rate, or quantity
that is not explicitly present in the JSON below. If a recommendation
would normally need a specific figure (e.g. an irrigation rate or
fertilizer dose) and no such figure exists in the JSON, write that this
project's data does not specify a value, rather than estimating one.

Do not add outside knowledge. Explain technical terms in plain language.
Explicitly state any data limitations listed in data_gaps."""


def _require_client():
    if _client is None:
        raise RuntimeError(
            "MISTRAL_API_KEY not set. Get a free key at console.mistral.ai "
            "or point config.py at a self-hosted open-weight Mistral endpoint."
        )


def _normalize_data_gaps(raw_gaps: list) -> list[str]:
    normalized = []
    for item in raw_gaps:
        if isinstance(item, str):
            normalized.append(item)
        elif isinstance(item, dict):
            text = item.get("gap") or item.get("description") or item.get("text")
            normalized.append(text if text else json.dumps(item, ensure_ascii=False))
        else:
            normalized.append(str(item))
    return normalized


def _validate_grounded_claims(raw_claims: list, valid_chunk_ids: set[str]) -> list[dict]:
    """
    Layer 1: drop any claim whose source_chunk_id doesn't match a chunk
    that was actually retrieved. This catches the model citing a
    plausible-looking but fabricated or hallucinated chunk_id.
    """
    validated = []
    for item in raw_claims:
        if not isinstance(item, dict):
            continue
        chunk_id = item.get("source_chunk_id")
        if chunk_id in valid_chunk_ids:
            validated.append(item)
    return validated


# Matches numbers with optional decimal (comma OR period), optional unit-ish suffix.
_NUMBER_PATTERN = re.compile(r"\d+(?:[.,]\d+)?\s*(?:%|°c|mm|kg|ha|g/kg|kg/ha|kg/n|n/ha)?", re.IGNORECASE)

_TOLERANCE_ABS = 0.05   # absolute float difference allowed (covers rounding to 2dp)
_TOLERANCE_REL = 0.01   # relative difference allowed (covers 1% rounding on larger numbers)


def _parse_number_token(tok: str) -> float | None:
    """Extracts the numeric value from a token, handling both French
    (comma) and JSON (period) decimal separators. Returns None for
    tokens with no digits (shouldn't happen given _NUMBER_PATTERN, but
    defensive)."""
    digits_part = re.match(r"\d+(?:[.,]\d+)?", tok.strip())
    if not digits_part:
        return None
    return float(digits_part.group().replace(",", "."))


def _values_match(a: float, b: float) -> bool:
    if abs(a - b) <= _TOLERANCE_ABS:
        return True
    if b != 0 and abs(a - b) / abs(b) <= _TOLERANCE_REL:
        return True
    return False


def _collect_source_values(synthesis: SynthesisJSON, parcel: ParcelResolution) -> set[float]:
    """
    Gathers every numeric VALUE that legitimately appears in the source
    data — soil, weather (both Stage 1's summary AND the Python-computed
    weather_stats), vegetation, the DL observation, parcel fields (area),
    crop recommendations, and grounded claims — PLUS every crop's
    score*100 and the DL confidence*100 (legitimate derived numbers, not
    invention). Values, not strings: this is immune to comma-vs-period
    and unit-suffix formatting differences between JSON and French prose.
    """
    values = set()
    searchable_text = json.dumps(synthesis.soil_summary, ensure_ascii=False)
    searchable_text += json.dumps(synthesis.weather_summary, ensure_ascii=False)
    searchable_text += json.dumps(synthesis.weather_stats, ensure_ascii=False)
    searchable_text += json.dumps(synthesis.vegetation_summary, ensure_ascii=False)
    searchable_text += json.dumps(synthesis.dl_observation_summary, ensure_ascii=False)
    searchable_text += json.dumps(synthesis.agro_calc_summary, ensure_ascii=False)
    searchable_text += json.dumps(
        [c.model_dump() for c in synthesis.crop_recommendations], ensure_ascii=False
    )
    searchable_text += json.dumps(synthesis.grounded_claims, ensure_ascii=False)
    if synthesis.dl_mismatch_note:
        searchable_text += synthesis.dl_mismatch_note
    if parcel.area_ha is not None:
        searchable_text += json.dumps({"area_ha": parcel.area_ha, "area_m2": parcel.area_m2})

    for match in _NUMBER_PATTERN.finditer(searchable_text):
        val = _parse_number_token(match.group())
        if val is not None:
            values.add(val)

    # Allow the derived percentage form of each crop score (e.g. 0.87 -> 87)
    for rec in synthesis.crop_recommendations:
        values.add(round(rec.suitability_score * 100))

    # Allow the derived percentage form of the DL confidence (e.g. 0.82 -> 82)
    if synthesis.dl_observation_summary.get("confidence") is not None:
        values.add(round(synthesis.dl_observation_summary["confidence"] * 100))

    return values


def _audit_report_numbers(report_text: str, synthesis: SynthesisJSON, parcel: ParcelResolution) -> list[str]:
    """
    Layer 3: extracts every number-looking token from the generated
    report, parses it to a float, and flags ones with no matching value
    (within a small tolerance) anywhere in the source data. Returns the
    original French-formatted string (not the parsed float) so the
    report to the user still reads naturally, e.g. "23,7" not "23.7".
    """
    source_values = _collect_source_values(synthesis, parcel)

    unverified = []
    for match in _NUMBER_PATTERN.finditer(report_text):
        tok = match.group().strip()
        has_unit_or_decimal = any(c.isalpha() or c in "%,." for c in tok)
        if not has_unit_or_decimal:
            continue
        val = _parse_number_token(tok)
        if val is None:
            continue
        if not any(_values_match(val, sv) for sv in source_values):
            unverified.append(tok)

    return sorted(set(unverified))


async def synthesize_stage1(
    parcel: ParcelResolution,
    soil: SoilData,
    weather: WeatherData,
    crop_recs: list[CropRecommendation],
    chunks: list[RetrievedChunk],
    vegetation: VegetationData,
    dl_observation: DLCropObservation,
    agro_calc: AgroCalcEstimate,
) -> SynthesisJSON:
    _require_client()

    # dl_observation is deliberately NOT included in the Stage 1 payload —
    # it never reaches the LLM, so there's no path for Stage 1 to
    # "helpfully" reformat, recompute, or misstate it (the exact failure
    # mode found with weather_summary's temperature mean). It's merged
    # straight into the returned SynthesisJSON below as pre-verified data.
    weather_stats = compute_weather_stats(weather)

    payload = {
        "parcel": parcel.model_dump(),
        "soil": soil.model_dump(),
        "weather": weather.model_dump(),
        "weather_precomputed": weather_stats,  # authoritative aggregates — Stage 1 must use these, not compute its own
        "vegetation": vegetation.model_dump(),
        "crop_recommendations": [c.model_dump() for c in crop_recs],
        "retrieved_chunks": [
            {"chunk_id": c.chunk_id, "text": c.text, "source_document": c.source_document}
            for c in chunks
        ],
    }

    # _client.chat.complete is the SYNCHRONOUS Mistral SDK call — run it in
    # a worker thread so it doesn't block the asyncio event loop. Without
    # this, the entire server (including serving every other request)
    # freezes for the whole duration of the LLM call.
    resp = await asyncio.to_thread(
        _client.chat.complete,
        model=settings.mistral_model,
        temperature=0.1,
        response_format={"type": "json_object"},
        messages=[
            {"role": "system", "content": _STAGE1_SYSTEM},
            {"role": "user", "content": json.dumps(payload, ensure_ascii=False)},
        ],
    )
    raw = json.loads(resp.choices[0].message.content)

    valid_chunk_ids = {c.chunk_id for c in chunks}

    dl_mismatch_note = None
    if dl_observation.source != "unavailable":
        from app.services.dl_service import crops_roughly_match
        match = crops_roughly_match(parcel.crop_declared, dl_observation.predicted_class_fr)
        if match is False:
            dl_mismatch_note = (
                f"Le RPG déclare « {parcel.crop_declared} » pour cette parcelle, mais l'analyse "
                f"satellite (IA) y observe actuellement « {dl_observation.predicted_class_fr} » "
                f"(confiance : {round(dl_observation.confidence * 100)}%). Cela peut indiquer une "
                f"déclaration RPG obsolète, une parcelle en rotation, une jachère, ou un changement "
                f"récent d'exploitant — à vérifier avant toute décision."
            )

    return SynthesisJSON(
        parcel_id=parcel.parcel_id,
        location=parcel.centroid,
        soil_summary=soil.model_dump(),
        weather_summary=weather.model_dump(),
        weather_stats=weather_stats,
        vegetation_summary=vegetation.model_dump(),
        dl_observation_summary=dl_observation.model_dump(),
        dl_mismatch_note=dl_mismatch_note,
        agro_calc_summary=agro_calc.model_dump(),
        crop_recommendations=crop_recs,
        grounded_claims=_validate_grounded_claims(raw.get("grounded_claims", []), valid_chunk_ids),
        data_gaps=_normalize_data_gaps(raw.get("data_gaps", [])),
    )


async def generate_report(synthesis: SynthesisJSON, parcel: ParcelResolution) -> AdvisorReport:
    """
    parcel is passed in separately so Stage 2 can be given the land area
    explicitly — SynthesisJSON doesn't carry it (only location).
    """
    _require_client()

    payload = {
        "synthesis": json.loads(synthesis.model_dump_json()),
        "parcel": parcel.model_dump(),
    }

    resp = await asyncio.to_thread(
        _client.chat.complete,
        model=settings.mistral_model,
        temperature=0.2,
        messages=[
            {"role": "system", "content": _STAGE2_SYSTEM},
            {"role": "user", "content": json.dumps(payload, ensure_ascii=False)},
        ],
    )
    report_text = resp.choices[0].message.content

    unverified = _audit_report_numbers(report_text, synthesis, parcel)

    return AdvisorReport(
        parcel_id=synthesis.parcel_id,
        report_markdown=report_text,
        warnings=synthesis.data_gaps,
        unverified_figures=unverified,
    )
