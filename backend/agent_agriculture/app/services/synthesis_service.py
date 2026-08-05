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
    YieldEstimate,
)
from app.taxonomy import get_display_name
from app.services.source_links import HAL_ID_RE, source_url_for_document

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

## Rendement estimé
If yield_summary.yield_estimate_q_ha is present, state it as:
- **Rendement estimé** : {yield_estimate_q_ha} q/ha (fourchette {yield_range_low_q_ha} – {yield_range_high_q_ha} q/ha)
Then copy method_note verbatim. If yield_summary is empty, omit this section.

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
PRIMARY content = document RAG only (chroma_store).
Output a bulleted list with EVERY item from synthesis.practical_tips,
copied verbatim (you may fix punctuation only). Do NOT invent extra
conseils from soil/weather/NDVI/crop scores — those belong elsewhere.
If practical_tips is empty, write exactly:
"- Aucun conseil documentaire retrouvé dans le corpus RAG."
Then, IF synthesis.practical_tips_context is non-empty, add a blank
line and the subheading "### Contexte parcelle" followed by EVERY
item from practical_tips_context as bullets, copied verbatim, at the
BOTTOM of this section only.

## Alertes
PRIMARY content = document RAG only (chroma_store).
Output a bulleted list with EVERY item from synthesis.alerts, copied
verbatim. Do NOT invent alerts from soil/weather/NDVI/RPG mismatch —
those go only under context. If alerts is empty, write exactly:
"- Aucune alerte documentaire retrouvée dans le corpus RAG."
Then, IF synthesis.alerts_context is non-empty, add a blank line and
the subheading "### Contexte parcelle" followed by EVERY item from
alerts_context as bullets, copied verbatim, at the BOTTOM of this
section only.

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


_ALERT_KEYWORDS = (
    "risque", "alerte", "perte", "lixiviation", "lessivage", "stress",
    "maladie", "danger", "attention", "éviter", "évite", "toxicité",
    "carence", "excès", "pollution", "nitrate", "lessiv",
)


def _build_rag_tips_and_alerts(
    grounded_claims: list[dict],
    chunks: list[RetrievedChunk],
) -> tuple[list[str], list[str]]:
    """Primary Conseils / Alertes content — chroma RAG grounded claims only."""
    tips: list[str] = []
    alerts: list[str] = []
    chunk_meta = {
        c.chunk_id: (c.source_document, c.source_url) for c in chunks
    }
    for claim in grounded_claims:
        text = claim.get("claim", "").strip()
        src_id = claim.get("source_chunk_id")
        if not text:
            continue
        src_name, src_url = chunk_meta.get(src_id, ("document agronomique", None))
        url = src_url or source_url_for_document(src_name)
        hal_match = HAL_ID_RE.match(src_name)
        link_label = hal_match.group("hal_id") if hal_match else (
            src_name.replace(".pdf", "")[:48] if src_name.endswith(".pdf") else src_name
        )
        if url:
            citation = f"(Source : [{link_label}]({url}))"
        else:
            citation = f"(Source : {src_name})"
        bullet = f"{text} {citation}"
        lower = text.lower()
        if any(k in lower for k in _ALERT_KEYWORDS) and len(alerts) < 6:
            alerts.append(bullet)
        elif len(tips) < 6:
            tips.append(bullet)
    return tips, alerts


def _build_parcel_context_tips_and_alerts(
    parcel: ParcelResolution,
    soil: SoilData,
    weather_stats: dict,
    vegetation: VegetationData,
    crop_recs: list[CropRecommendation],
    agro_calc: AgroCalcEstimate | None,
    yield_estimate: YieldEstimate | None,
    dl_mismatch_note: str | None,
) -> tuple[list[str], list[str]]:
    """Parcel-data bullets — shown only under ### Contexte parcelle at section bottom."""
    tips: list[str] = []
    alerts: list[str] = []

    top = crop_recs[0] if crop_recs else None
    if top:
        crop_label = get_display_name(top.crop)
        score_pct = round(top.suitability_score * 100)
        tips.append(
            f"Culture la plus compatible avec cette parcelle : {crop_label} "
            f"(score {score_pct} %). Croisez ce résultat avec votre rotation "
            f"et vos contrats avant de décider."
        )
        if score_pct < 55:
            alerts.append(
                f"Compatibilité modérée pour {crop_label} ({score_pct} %). "
                f"Envisagez les autres cultures recommandées ou un diagnostic sol plus fin."
            )

    if parcel.crop_declared:
        declared = get_display_name(parcel.crop_declared)
        tips.append(
            f"Culture déclarée au RPG pour cette parcelle : {declared}. "
            f"Vérifiez qu'elle reste cohérente avec votre plan de rotation."
        )

    if soil.ph is not None:
        if soil.ph < 6.0:
            tips.append(
                f"Sol plutôt acide (pH {soil.ph:.1f}). Un chaulage peut être utile "
                f"selon la culture visée — à confirmer par analyse."
            )
        elif soil.ph > 7.8:
            tips.append(
                f"Sol plutôt basique (pH {soil.ph:.1f}). Certaines cultures "
                f"(colza, betterave) s'y adaptent mieux que d'autres."
            )

    if agro_calc and agro_calc.n_dose_kg_ha is not None:
        tips.append(
            f"Dose d'azote estimée pour la culture principale : "
            f"{agro_calc.n_dose_kg_ha:.1f} kg N/ha (estimation SoilGrids, "
            f"à valider par analyse de sol)."
        )

    if agro_calc and agro_calc.irrigation_need_mm is not None and agro_calc.irrigation_window_days:
        need = agro_calc.irrigation_need_mm
        days = agro_calc.irrigation_window_days
        tips.append(
            f"Besoin d'irrigation estimé sur {days} jours : {need:.1f} mm. "
            f"Planifiez l'irrigation en fonction de la météo réelle du jour."
        )
        if need >= 80:
            alerts.append(
                f"Besoin d'irrigation élevé ({need:.1f} mm sur {days} jours). "
                f"Surveillez l'humidité et anticipez les apports d'eau."
            )

    if yield_estimate and yield_estimate.yield_estimate_q_ha is not None:
        tips.append(
            f"Rendement estimé pour la culture principale : "
            f"{yield_estimate.yield_estimate_q_ha:.1f} q/ha "
            f"(fourchette indicative, pas une garantie de récolte)."
        )

    total_precip = weather_stats.get("total_precip_mm")
    rainy_days = weather_stats.get("rainy_days_count")
    if total_precip is not None and rainy_days is not None:
        if total_precip < 15 and rainy_days <= 2:
            alerts.append(
                f"Période récente plutôt sèche ({total_precip:.1f} mm sur "
                f"{rainy_days} jour(s) de pluie). Surveillez le stress hydrique."
            )
        elif total_precip > 80:
            alerts.append(
                f"Précipitations cumulées élevées ({total_precip:.1f} mm). "
                f"Évitez le travail du sol saturé et surveillez les maladies fongiques."
            )

    if vegetation.source == "sentinel-2" and vegetation.mean_ndvi is not None:
        ndvi = vegetation.mean_ndvi
        if ndvi < 0.2:
            alerts.append(
                f"NDVI faible ({ndvi:.2f}) : couvert végétal sparse ou sol nu. "
                f"Utile comme contexte, pas comme diagnostic de rendement."
            )
        elif ndvi > 0.55:
            tips.append(
                f"Végétation active sur la parcelle (NDVI moyen {ndvi:.2f}). "
                f"Contexte satellite utile pour le suivi, indépendamment du choix de culture."
            )
    elif vegetation.source == "unavailable":
        alerts.append(
            "Données satellite Sentinel-2 indisponibles pour cette parcelle "
            "(nuages, credentials ou couverture). Le reste de l'analyse reste valide."
        )

    if dl_mismatch_note:
        alerts.append(dl_mismatch_note)

    return tips, alerts


def _format_section_body(rag_bullets: list[str], context_bullets: list[str], empty_msg: str) -> str:
    """RAG bullets first; parcel-context bullets under a bottom subheading."""
    primary = "\n".join(f"- {b}" for b in rag_bullets) if rag_bullets else f"- {empty_msg}"
    if not context_bullets:
        return primary
    ctx = "\n".join(f"- {b}" for b in context_bullets)
    return f"{primary}\n\n### Contexte parcelle\n{ctx}"


def _inject_section_bullets(
    report_text: str,
    section_title: str,
    rag_bullets: list[str],
    context_bullets: list[str],
    empty_msg: str,
) -> str:
    """Replace ## section body with RAG primary + context at the bottom."""
    block = _format_section_body(rag_bullets, context_bullets, empty_msg)
    needle = f"## {section_title}"
    idx = report_text.find(needle)
    if idx == -1:
        return report_text.rstrip() + f"\n\n{needle}\n{block}\n"
    start = idx + len(needle)
    next_idx = report_text.find("\n## ", start)
    if next_idx == -1:
        return report_text[:start] + "\n" + block + "\n"
    return report_text[:start] + "\n" + block + "\n" + report_text[next_idx:]


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
    searchable_text += json.dumps(synthesis.yield_summary, ensure_ascii=False)
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
    yield_estimate: YieldEstimate | None = None,
) -> SynthesisJSON:
    _require_client()

    # dl_observation / agro_calc / yield_estimate are deliberately NOT included
    # in the Stage 1 payload — they never reach the LLM, so there's no path for
    # Stage 1 to "helpfully" reformat or misstate them. They're merged straight
    # into the returned SynthesisJSON below as pre-verified data.
    weather_stats = compute_weather_stats(weather)

    payload = {
        "parcel": parcel.model_dump(),
        "soil": soil.model_dump(),
        "weather": weather.model_dump(),
        "weather_precomputed": weather_stats,  # authoritative aggregates — Stage 1 must use these, not compute its own
        "vegetation": vegetation.model_dump(),
        "crop_recommendations": [c.model_dump() for c in crop_recs],
        "retrieved_chunks": [
            {
                "chunk_id": c.chunk_id,
                "text": c.text,
                "source_document": c.source_document,
                "source_url": c.source_url,
            }
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

    validated_claims = _validate_grounded_claims(raw.get("grounded_claims", []), valid_chunk_ids)
    data_gaps = _normalize_data_gaps(raw.get("data_gaps", []))
    if not chunks and not any("rag" in g.lower() or "corpus" in g.lower() for g in data_gaps):
        data_gaps.append(
            "Corpus documentaire RAG vide ou non indexé — conseils documentaires limités."
        )

    practical_tips, alerts = _build_rag_tips_and_alerts(
        grounded_claims=validated_claims,
        chunks=chunks,
    )
    practical_tips_context, alerts_context = _build_parcel_context_tips_and_alerts(
        parcel=parcel,
        soil=soil,
        weather_stats=weather_stats,
        vegetation=vegetation,
        crop_recs=crop_recs,
        agro_calc=agro_calc,
        yield_estimate=yield_estimate,
        dl_mismatch_note=dl_mismatch_note,
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
        yield_summary=yield_estimate.model_dump() if yield_estimate else {},
        crop_recommendations=crop_recs,
        grounded_claims=validated_claims,
        data_gaps=data_gaps,
        practical_tips=practical_tips,
        alerts=alerts,
        practical_tips_context=practical_tips_context,
        alerts_context=alerts_context,
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
    report_text = _inject_section_bullets(
        report_text,
        "Conseils pratiques",
        synthesis.practical_tips,
        synthesis.practical_tips_context,
        "Aucun conseil documentaire retrouvé dans le corpus RAG.",
    )
    report_text = _inject_section_bullets(
        report_text,
        "Alertes",
        synthesis.alerts,
        synthesis.alerts_context,
        "Aucune alerte documentaire retrouvée dans le corpus RAG.",
    )

    unverified = _audit_report_numbers(report_text, synthesis, parcel)

    return AdvisorReport(
        parcel_id=synthesis.parcel_id,
        report_markdown=report_text,
        warnings=synthesis.data_gaps,
        unverified_figures=unverified,
    )
