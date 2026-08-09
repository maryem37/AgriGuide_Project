"""
pipeline.py
------------
Orchestrates the full hybrid flow: farmer input -> RAG retrieval ->
yield estimate -> fact extraction -> economic calculation -> narrative report.

This is the single function app.py should call.

    from backend.pipeline import generate_full_report
    result = generate_full_report({
        "crop": "Blé tendre",
        "area_ha": 10,
        "location": "France",
        "irrigation": "Irrigué",          # or "Non irrigué"
        "production_method": "Conventionnelle",  # or "Biologique"
        "budget": 8000,                    # optional, in EUR
    })

result is a dict with:
    "indicators": {...}      # the numbers, from EconomicReport.to_dict()
    "narrative": "..."       # Groq-written markdown report
    "sources_used": [...]    # which PDFs/CSV series informed the numbers
    "warnings": [...]        # e.g. "price extraction failed, used fallback"
"""

from __future__ import annotations

import sys
from pathlib import Path
from typing import Optional

sys.path.insert(0, str(Path(__file__).resolve().parent))
sys.path.insert(0, str(Path(__file__).resolve().parent / "rag"))
from rag import config as csv_config          # noqa: E402
from rag import csv_retriever                  # noqa: E402
from rag import crop_mapping                    # noqa: E402
from rag import embedder                       # noqa: E402
from backend.profit_analysis.calculator import (              # noqa: E402
    EconomicInputs,
    compute_report,
)
import groq_client                              # noqa: E402


# Heuristic yield adjustment factors. These are placeholders for the
# "predictive AI" model — swap _adjust_yield() for a trained model's
# prediction once you have one; the rest of the pipeline doesn't change.
IRRIGATION_FACTOR = {
    "irrigué": 1.15,
    "irrigue": 1.15,
    "non irrigué": 0.90,
    "non irrigue": 0.90,
}
METHOD_FACTOR = {
    "biologique": 0.85,
    "conventionnelle": 1.0,
    "conventionnel": 1.0,
}

# Fallback cost/price when extraction from PDFs fails entirely — clearly
# flagged as low-confidence rather than silently trusted.
FALLBACK_COST_PER_HA = 900.0
FALLBACK_PRICE_PER_TON = 200.0


def _normalize_key(text: Optional[str]) -> str:
    return (text or "").strip().lower()


def _adjust_yield(base_yield_t_ha: float, irrigation: str, production_method: str) -> float:
    irr_factor = IRRIGATION_FACTOR.get(_normalize_key(irrigation), 1.0)
    method_factor = METHOD_FACTOR.get(_normalize_key(production_method), 1.0)
    return base_yield_t_ha * irr_factor * method_factor


def _gather_yield_estimate(crop: str, location: str, irrigation: str, production_method: str) -> dict:
    """
    CSV-based (FAO) yield baseline, adjusted by irrigation/method heuristics.

    The farmer's crop name (often French, informal — "mais", "ble") rarely
    matches FAO's English Item names ("Maize (corn)", "Wheat") via plain
    substring search. crop_mapping resolves that first; if it still can't
    find a match, we fall back to the raw crop string (which may still work
    for crops the farmer already typed in English/matching form).
    """
    fao_df = csv_retriever.load_fao_data(csv_config.FAO_YIELD_CSV)

    resolved_item = crop_mapping.resolve_crop_to_fao_item(crop, fao_df["Item"])
    lookup_term = resolved_item if resolved_item else crop

    stats = csv_retriever.estimate_expected_yield(fao_df, lookup_term, area=location or "France")

    if stats["mean_t_per_ha"] is None:
        return {
            "predicted_yield_t_per_ha": 0.0,
            "yield_std_t_per_ha": None,
            "n_yield_data_points": 0,
            "warning": (
                f"No historical FAO yield data found for crop='{crop}' "
                f"(resolved to '{resolved_item}')" if resolved_item else
                f"No historical FAO yield data found for crop='{crop}', area='{location}'. "
                f"Crop name not recognized — consider adding it to crop_mapping.py."
            ),
        }

    adjusted = _adjust_yield(stats["mean_t_per_ha"], irrigation, production_method)
    return {
        "predicted_yield_t_per_ha": adjusted,
        "yield_std_t_per_ha": stats["std_t_per_ha"],
        "n_yield_data_points": stats["n_points"],
        "warning": None,
    }


def _gather_price_index_context(crop: str) -> Optional[float]:
    """Latest IPAMPA input-cost index value, for narrative context only — not a direct €/ha figure."""
    try:
        catalog = csv_retriever.load_caracteristiques(csv_config.CARACTERISTIQUES_CSV)
        annual = csv_retriever.load_insee_wide_values(csv_config.VALEURS_ANNUELLES_CSV)
        return csv_retriever.latest_price_index(annual, catalog, crop)
    except Exception:
        return None


def _gather_pdf_context(crop: str, n_results_per_query: int = 6) -> list[dict]:
    """
    Retrieves PDF chunks likely to contain cost/price info for this crop.

    Two mitigations against a large, diverse PDF collection drowning out the
    right crop with semantically-similar-but-wrong content:
      1. Multiple query phrasings (cost AND price AND the crop's FAO-resolved
         name, if different from the raw input) instead of one narrow query.
      2. Post-filter: keep only chunks whose text actually mentions the crop
         (or its resolved English name). If that empties the result set
         entirely (e.g. very sparse PDF coverage), fall back to the
         unfiltered top matches rather than returning nothing — but tag them
         as unverified so extraction/reporting can treat them cautiously.
    """
    fao_df = csv_retriever.load_fao_data(csv_config.FAO_YIELD_CSV)
    resolved_item = crop_mapping.resolve_crop_to_fao_item(crop, fao_df["Item"])

    search_terms = [crop]
    if resolved_item and csv_retriever._normalize(resolved_item) != csv_retriever._normalize(crop):
        search_terms.append(resolved_item)

    queries = []
    for term in search_terms:
        queries.append(f"coût de production {term}")
        queries.append(f"prix de vente {term}")

    all_chunks: dict[str, dict] = {}  # keyed by text to dedupe
    for q in queries:
        try:
            for chunk in embedder.query_docs(q, n_results=n_results_per_query):
                all_chunks[chunk["text"]] = chunk
        except Exception:
            continue

    candidates = list(all_chunks.values())
    if not candidates:
        return []

    # Post-filter to chunks that actually mention the crop
    keywords_norm = {csv_retriever._normalize(t) for t in search_terms}
    filtered = [
        c for c in candidates
        if any(kw in csv_retriever._normalize(c["text"]) for kw in keywords_norm)
    ]

    if filtered:
        return sorted(filtered, key=lambda c: c["distance"])[:8]

    # Nothing explicitly mentioned the crop — fall back to unfiltered top
    # matches but tag them so the caller/report can flag lower trust.
    for c in candidates:
        c["crop_keyword_matched"] = False
    return sorted(candidates, key=lambda c: c["distance"])[:8]


def generate_full_report(farmer_input: dict) -> dict:
    warnings: list[str] = []
    sources_used: list[str] = []

    crop = farmer_input["crop"]
    area_ha = float(farmer_input["area_ha"])
    location = farmer_input.get("location", "France")
    irrigation = farmer_input.get("irrigation", "")
    production_method = farmer_input.get("production_method", "")
    budget = farmer_input.get("budget")

    # --- 1. Yield estimate (CSV-based baseline + heuristic adjustment) ----
    yield_info = _gather_yield_estimate(crop, location, irrigation, production_method)
    if yield_info["warning"]:
        warnings.append(yield_info["warning"])

    # --- 2. Retrieve PDF context for cost & price ---------------------------
    context_chunks = _gather_pdf_context(crop)
    sources_used.extend({c["source"] for c in context_chunks})
    crop_confirmed_in_text = any(
        c.get("crop_keyword_matched", True) for c in context_chunks
    ) if context_chunks else False
    if context_chunks and not crop_confirmed_in_text:
        warnings.append(
            f"No retrieved PDF passages explicitly mention '{crop}'; the closest "
            f"matches by semantic similarity were used, but may not be crop-specific. "
            f"Consider adding a PDF with cost/price data for this crop."
        )

    # --- 3. Extract raw numeric facts from that PDF text via Groq -----------
    facts = groq_client.extract_price_cost_facts(
        crop=crop,
        context_chunks=context_chunks,
        location=location,
    )

    price_per_ton = facts.get("price_per_ton_eur")
    cost_per_ha = facts.get("cost_per_ha_eur")
    exact_region_match = bool(context_chunks) and crop_confirmed_in_text

    if price_per_ton is None:
        warnings.append(
            f"Could not extract a selling price from retrieved documents; "
            f"using fallback of {FALLBACK_PRICE_PER_TON} €/t. Verify manually."
        )
        price_per_ton = FALLBACK_PRICE_PER_TON

    if cost_per_ha is None:
        warnings.append(
            f"Could not extract a production cost from retrieved documents; "
            f"using fallback of {FALLBACK_COST_PER_HA} €/ha. Verify manually."
        )
        cost_per_ha = FALLBACK_COST_PER_HA

    # --- 4. Deterministic economic calculation (no LLM) ---------------------
    inputs = EconomicInputs(
        crop=crop,
        area_ha=area_ha,
        predicted_yield_t_per_ha=yield_info["predicted_yield_t_per_ha"],
        price_per_ton=price_per_ton,
        cost_per_ha=cost_per_ha,
        farmer_budget=float(budget) if budget is not None else None,
        yield_std_t_per_ha=yield_info["yield_std_t_per_ha"],
        n_yield_data_points=yield_info["n_yield_data_points"],
        exact_region_match=exact_region_match,
        price_data_recency_years=0 if context_chunks else None,
    )
    report = compute_report(inputs)
    indicators = report.to_dict()

    # --- 5. Narrative generation (Groq narrates, never recalculates) --------
    narrative = groq_client.generate_narrative_report(
        farmer_input=farmer_input,
        economic_report=indicators,
        context_snippets=context_chunks,
    )

    return {
        "indicators": indicators,
        "narrative": narrative,
        "sources_used": sorted(sources_used),
        "warnings": warnings,
        "extraction_detail": {
            "price_evidence": facts.get("price_evidence"),
            "cost_evidence": facts.get("cost_evidence"),
            "extraction_confidence": facts.get("extraction_confidence"),
        },
    }


if __name__ == "__main__":
    # Structural check only (embedder/groq calls need a populated Chroma
    # store + GROQ_API_KEY, neither available in this dev sandbox).
    print("pipeline.py imports resolve correctly.")
    print("Run generate_full_report({...}) after: (1) embedder --ingest has been run,")
    print("(2) GROQ_API_KEY is set in your environment / .env file.")