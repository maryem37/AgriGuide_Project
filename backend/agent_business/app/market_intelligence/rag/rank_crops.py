"""
Score / rank crops with FranceAgriMer RAG + Agreste trend + Mistral JSON.
"""

from __future__ import annotations

import json
import time

from app.market_intelligence.crop_aliases import display_name
from app.market_intelligence.price_trends import compute_price_trend
from app.market_intelligence.rag.diagnose_crops import CHAT_MODEL, complete_chat
from app.market_intelligence.rag.retriever import retrieve

TOP_K_PER_CROP = 6

SYSTEM_PROMPT = """Tu es un conseiller agricole qui évalue la rentabilité de cultures
pour le marché français. Réponds UNIQUEMENT avec un objet JSON valide, structuré
exactement ainsi:
{
  "culture": "<nom de la culture>",
  "score": <nombre entre 0 et 10>,
  "tendance_prix": "<hausse|stable|baisse|inconnue>",
  "demande": "<forte|moderee|faible|inconnue>",
  "concurrence": "<forte|moderee|faible|inconnue>",
  "justification": "<2-4 phrases maximum, en français, citant les sources utiles>",
  "donnees_suffisantes": <true ou false>
}

Règles importantes:
- Combine les données chiffrées (indice Agreste) et le contexte documentaire
  (bulletins FranceAgriMer). Si l'une des deux manque mais que l'autre est
  pertinente, utilise celle qui est disponible.
- Mets donnees_suffisantes à false UNIQUEMENT si les deux sources sont vides
  ou non pertinentes pour cette culture.
- Ne mets jamais un score au-dessus de 3 si donnees_suffisantes est false.
- N'invente jamais de chiffres absents des données fournies.
- Pour demande/concurrence, infère uniquement depuis le contexte PDF ; sinon "inconnue".
"""


def build_crop_prompt(crop_name: str, hits, trend) -> str:
    context_lines = []
    for i, hit in enumerate(hits, start=1):
        source = hit["metadata"].get("source", "unknown")
        extra = ""
        if "page" in hit["metadata"]:
            extra = f", page {hit['metadata']['page']}"
        elif "row" in hit["metadata"]:
            extra = f", row {hit['metadata']['row']}"
        context_lines.append(f"[{i}] ({source}{extra}) {hit['text']}")
    context_block = "\n\n".join(context_lines) if context_lines else "Aucun contexte trouvé."

    trend_block = "Aucune donnée d'indice de prix trouvée pour cette culture dans le CSV."
    if trend:
        parts = []
        if trend.get("pct_change") is not None:
            parts.append(
                f"variation de l'indice de prix sur la période récente: {trend['pct_change']}%"
            )
        if trend.get("latest_index") is not None:
            parts.append(f"dernier indice connu (base 100): {trend['latest_index']}")
        if trend.get("produit_label"):
            parts.append(f"série Agreste: {trend['produit_label']}")
        parts.append(f"nombre de points de données: {trend['data_points']}")
        trend_block = ", ".join(parts)

    return f"""Culture évaluée : {crop_name}

Données chiffrées calculées (Agreste IPPAP) :
{trend_block}

Contexte documentaire (bulletins FranceAgriMer / indices) :
{context_block}

Évalue l'opportunité de marché pour planter cette culture prochainement
(prix, demande, concurrence), en te basant uniquement sur les informations ci-dessus."""


def _retrieve_for_crop(crop_name: str) -> list[dict]:
    """Prefer PDF bulletins; fall back to any doc type if PDFs miss."""
    try:
        hits = retrieve(crop_name, top_k=TOP_K_PER_CROP, where={"doc_type": "pdf"})
    except Exception:
        hits = []
    if len(hits) >= 2:
        return hits
    try:
        more = retrieve(crop_name, top_k=TOP_K_PER_CROP)
    except Exception:
        more = []
    if not hits:
        return more
    # Merge unique texts
    seen = {h["text"] for h in hits}
    for h in more:
        if h["text"] not in seen:
            hits.append(h)
            seen.add(h["text"])
        if len(hits) >= TOP_K_PER_CROP:
            break
    return hits


def score_crop(crop_name: str) -> dict:
    """Scores a single crop: retrieval + computed trend -> structured JSON verdict."""
    label = display_name(crop_name)
    t0 = time.perf_counter()
    hits = _retrieve_for_crop(label)
    retrieval_time = time.perf_counter() - t0

    trend = compute_price_trend(crop_name)
    user_message = build_crop_prompt(label, hits, trend)

    t1 = time.perf_counter()
    response = complete_chat(
        model=CHAT_MODEL,
        messages=[
            {"role": "system", "content": SYSTEM_PROMPT},
            {"role": "user", "content": user_message},
        ],
        response_format={"type": "json_object"},
        temperature=0.2,
        random_seed=42,
    )
    generation_time = time.perf_counter() - t1

    raw = response.choices[0].message.content
    try:
        parsed = json.loads(raw)
    except json.JSONDecodeError:
        parsed = {
            "culture": label,
            "score": 0,
            "tendance_prix": "inconnue",
            "demande": "inconnue",
            "concurrence": "inconnue",
            "justification": "Erreur: réponse du modèle non parsable.",
            "donnees_suffisantes": False,
        }

    parsed.setdefault("demande", "inconnue")
    parsed.setdefault("concurrence", "inconnue")
    parsed["stats"] = {
        "chunks_trouves": len(hits),
        "sources": sorted({h["metadata"].get("source", "unknown") for h in hits}),
        "avg_rerank_score": (
            round(sum(h.get("rerank_score", 0) for h in hits) / len(hits), 4) if hits else None
        ),
        "tendance_csv": trend,
        "retrieval_time_s": round(retrieval_time, 3),
        "generation_time_s": round(generation_time, 3),
    }
    return parsed


def rank_crops(crops: list, top_n: int = 3) -> dict:
    results = [score_crop(crop) for crop in crops]
    results.sort(key=lambda r: r.get("score", 0), reverse=True)
    return {"top": results[:top_n], "all_evaluated": results}
