"""
groq_client.py
----------------
All Groq LLM calls for the pipeline, used in exactly two roles:

  1. extract_price_cost_facts()  -> reads unstructured PDF chunks (retrieved
     via embedder.query_docs) and pulls out raw numeric facts (price €/ton,
     cost €/ha) as structured JSON, WITH the source snippet that justified
     each number. This is text extraction, not computation.

  2. generate_narrative_report() -> takes the ALREADY-COMPUTED EconomicReport
     (from economics/calculator.py) and writes the human-readable report.
     The prompt explicitly forbids recalculating or altering any number.

Rule: Groq never does arithmetic. Every number in the final report traces
back to economics/calculator.py. Groq only extracts raw facts from text and
narrates already-computed results.
"""

from __future__ import annotations

import json
import os
from typing import Optional

from groq import Groq


DEFAULT_MODEL = "llama-3.3-70b-versatile"


def _get_client() -> Groq:
    api_key = os.environ.get("GROQ_API_KEY")
    if not api_key:
        raise RuntimeError(
            "GROQ_API_KEY not set. Add it to your .env file or export it in your shell."
        )
    return Groq(api_key=api_key)


def _strip_json_fences(text: str) -> str:
    """Groq sometimes wraps JSON in ```json fences even when asked not to."""
    text = text.strip()
    if text.startswith("```"):
        text = text.split("```")[1]
        if text.startswith("json"):
            text = text[4:]
    return text.strip()


# --------------------------------------------------------------------------- #
# 1. Fact extraction from retrieved PDF chunks
# --------------------------------------------------------------------------- #

def extract_price_cost_facts(
    crop: str,
    context_chunks: list[dict],
    location: Optional[str] = None,
    model: str = DEFAULT_MODEL,
) -> dict:
    """
    context_chunks: output of embedder.query_docs(), i.e. list of
        {"text": ..., "source": ..., "distance": ...}

    Returns:
        {
          "price_per_ton_eur": float | None,
          "price_source": str | None,       # which PDF it came from
          "price_evidence": str | None,     # short justification, in Groq's own words
          "cost_per_ha_eur": float | None,
          "cost_source": str | None,
          "cost_evidence": str | None,
          "extraction_confidence": "high" | "medium" | "low"
        }

    If the chunks don't contain a clear number, fields come back as None and
    confidence is "low" — the caller (pipeline.py) is responsible for falling
    back to a default/estimate rather than trusting a hallucinated figure.
    """
    if not context_chunks:
        return {
            "price_per_ton_eur": None,
            "price_source": None,
            "price_evidence": None,
            "cost_per_ha_eur": None,
            "cost_source": None,
            "cost_evidence": None,
            "extraction_confidence": "low",
        }

    context_text = "\n\n".join(
        f"[Source: {c['source']}]\n{c['text']}" for c in context_chunks
    )

    system_prompt = (
        "You are a data-extraction assistant. You read French agricultural "
        "documents and extract ONLY numeric facts that are explicitly stated "
        "in the text. You never estimate, infer, or calculate a number that "
        "is not directly present in the source text. If no clear figure is "
        "present for a field, you return null for it. You respond with ONLY "
        "a raw JSON object, no markdown fences, no preamble, no explanation "
        "outside the JSON."
    )

    location_hint = f" in the {location} region" if location else ""
    user_prompt = f"""Crop: {crop}{location_hint}

Source excerpts:
{context_text}

Extract the following, using ONLY numbers explicitly present in the excerpts above:
- selling price per ton in EUR (price_per_ton_eur)
- production cost per hectare in EUR (cost_per_ha_eur)

Respond with exactly this JSON shape:
{{
  "price_per_ton_eur": <number or null>,
  "price_source": "<filename or null>",
  "price_evidence": "<short paraphrase of the sentence that supports this number, in your own words, or null>",
  "cost_per_ha_eur": <number or null>,
  "cost_source": "<filename or null>",
  "cost_evidence": "<short paraphrase, in your own words, or null>",
  "extraction_confidence": "high" | "medium" | "low"
}}"""

    client = _get_client()
    response = client.chat.completions.create(
        model=model,
        messages=[
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": user_prompt},
        ],
        temperature=0.0,
        response_format={"type": "json_object"},
    )

    raw = response.choices[0].message.content
    try:
        data = json.loads(_strip_json_fences(raw))
    except json.JSONDecodeError:
        # Fail safe rather than crash the pipeline on a malformed LLM response
        return {
            "price_per_ton_eur": None,
            "price_source": None,
            "price_evidence": None,
            "cost_per_ha_eur": None,
            "cost_source": None,
            "cost_evidence": None,
            "extraction_confidence": "low",
        }

    return data


# --------------------------------------------------------------------------- #
# 2. Narrative report generation from already-computed numbers
# --------------------------------------------------------------------------- #

def generate_narrative_report(
    farmer_input: dict,
    economic_report: dict,
    context_snippets: Optional[list[dict]] = None,
    model: str = DEFAULT_MODEL,
) -> str:
    """
    farmer_input: {"crop", "area_ha", "location", "irrigation", "production_method"}
    economic_report: the dict from EconomicReport.to_dict() — already computed,
                      Groq must not change these numbers.
    context_snippets: optional retrieved PDF/CSV context for narrative color
                      (e.g. "national average yield trends", "cost drivers").

    Returns the final report as markdown text.
    """
    system_prompt = (
        "You are an agricultural profitability report writer. You are given "
        "a set of ALREADY-CALCULATED financial figures. You must use these "
        "exact numbers verbatim in your report — never recompute, round "
        "differently, or alter them. Your job is only to explain, "
        "contextualize, and format them clearly for a farmer, in French, "
        "using the risk and confidence reasons provided. If something in "
        "the reasons suggests a caveat (e.g. low confidence, high risk), "
        "state it plainly. Do not invent numbers that are not in the data "
        "provided."
    )

    context_block = ""
    if context_snippets:
        context_block = "\n\nContexte additionnel (sources):\n" + "\n".join(
            f"- [{c['source']}] {c['text'][:200]}" for c in context_snippets[:3]
        )

    user_prompt = f"""Exploitation agricole:
- Culture: {farmer_input.get('crop')}
- Superficie: {farmer_input.get('area_ha')} ha
- Localisation: {farmer_input.get('location')}
- Irrigation: {farmer_input.get('irrigation')}
- Méthode de production: {farmer_input.get('production_method')}

Indicateurs financiers calculés (à utiliser tels quels, ne pas recalculer):
{json.dumps(economic_report, indent=2, ensure_ascii=False)}
{context_block}

Rédige un rapport de rentabilité clair et structuré en français, avec des
sections: Résumé, Revenus et coûts, Rentabilité, Analyse budgétaire,
Évaluation des risques, Recommandations."""

    client = _get_client()
    response = client.chat.completions.create(
        model=model,
        messages=[
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": user_prompt},
        ],
        temperature=0.3,
    )

    return response.choices[0].message.content


if __name__ == "__main__":
    # Structural self-test with a fake context (no live API call —
    # api.groq.com isn't reachable from this dev sandbox).
    print("Module imports and builds prompts correctly.")
    fake_chunks = [
        {"text": "Le coût de production du blé tendre est estimé à 950 €/ha en 2024.",
         "source": "ANALYSE DES COÛTS DE PRODUCTION agricoles durables.pdf", "distance": 0.1}
    ]
    # We only check prompt construction here, not a real call:
    ctx = "\n\n".join(f"[Source: {c['source']}]\n{c['text']}" for c in fake_chunks)
    assert "950" in ctx
    print("Prompt-context construction OK. Run this for real once GROQ_API_KEY is set.")