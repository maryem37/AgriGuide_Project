"""
rank_crops.py
Takes a list of candidate crops (from an external/upstream agent) and
returns the top N, ranked using French market data.

Pipeline per crop:
1. Retrieve relevant chunks (retriever.py - vector search + reranking)
2. Compute a quantitative price trend directly from the raw CSV (pandas)
3. Ask Mistral for a structured JSON score, combining both signals
4. Sort all crops by score, return the top N
"""

import json
import time
import unicodedata
from pathlib import Path

import pandas as pd
from .ipap_parser import parse_ippap_csv
from .retriever import retrieve
from .diagnose_crops import CHAT_MODEL, complete_chat

TOP_K_PER_CROP = 5

# --- CSV config: matches the real Agreste IPPAP structure ---
BASE_DIR = Path(__file__).resolve().parent.parent
AGRESTE_DIR = BASE_DIR / "market" / "agreste"
CROP_COLUMN = "produit_nom"      # column holding the crop/product name
YEAR_COLUMN = "annee"            # year, combined with MONTH_COLUMN for sorting
MONTH_COLUMN = "mois_num"        # month number (1-12)
PRICE_COLUMN = "valeur"          # this is a PRICE INDEX (base 100), not a raw € price
HIERARCHY_COLUMN = "niveau_hierarchie"  # higher = more specific product, lower = broader category
# -------------------------------------------------------------------------

_csv_df = None


def _strip_accents(text: str) -> str:
    """Normalizes accented characters so 'maïs' matches 'Mais', 'blé' matches
    'ble', etc. - yearly CSV exports don't always spell products consistently."""
    if not isinstance(text, str):
        return text
    return "".join(
        c for c in unicodedata.normalize("NFKD", text)
        if not unicodedata.combining(c)
    )


def _load_csv() -> pd.DataFrame:
    """Loads and concatenates every CSV in the agreste folder (one per year)
    and caches the combined result in memory."""
    global _csv_df
    if _csv_df is not None:
        return _csv_df

    csv_files = sorted(AGRESTE_DIR.glob("*.csv")) if AGRESTE_DIR.exists() else []
    if not csv_files:
        print(f"[warn] No CSV found in {AGRESTE_DIR} - price trends will be unavailable.")
        _csv_df = pd.DataFrame()
        return _csv_df

    frames = []
    for f in csv_files:
        try:
            frames.append(parse_ippap_csv(f))
        except Exception as e:
            print(f"[warn] Could not parse {f.name}: {e}")

    if not frames:
        _csv_df = pd.DataFrame()
        return _csv_df

    _csv_df = pd.concat(frames, ignore_index=True)
    if CROP_COLUMN not in _csv_df.columns:
        print(
            f"[warn] Column '{CROP_COLUMN}' not found. "
            f"Available columns: {list(_csv_df.columns)}. "
            f"Update CROP_COLUMN/YEAR_COLUMN/MONTH_COLUMN/PRICE_COLUMN in rank_crops.py."
        )
    else:
        _csv_df["_produit_norm"] = (
            _csv_df[CROP_COLUMN].astype(str).apply(_strip_accents).str.lower()
        )
    return _csv_df


def compute_price_trend(crop_name: str, months: int = 6):
    """
    Returns a dict with a simple computed price INDEX trend for the crop, or
    None if no matching rows are found in the CSV.

    'valeur' is a price index (base 100), not a euro amount - pct_change
    still meaningfully reflects the direction/magnitude of price movement.
    """
    df = _load_csv()
    if df.empty or CROP_COLUMN not in df.columns or "_produit_norm" not in df.columns:
        return None

    crop_norm = _strip_accents(crop_name).lower()
    matches = df[df["_produit_norm"].str.contains(crop_norm, case=False, na=False)]
    if matches.empty:
        return None

    if "qualite" in matches.columns:
        validated = matches[matches["qualite"].astype(str).str.upper() == "OUI"]
        if not validated.empty:
            matches = validated

    # The CSV is hierarchical (e.g. "all agricultural products" at level 0,
    # down to a specific crop at a deeper level). If the crop name matches
    # more than one distinct product label, keep only the most specific one
    # (highest niveau_hierarchie) instead of mixing broad + specific data.
    if HIERARCHY_COLUMN in matches.columns and matches[CROP_COLUMN].nunique() > 1:
        max_level = matches[HIERARCHY_COLUMN].max()
        best_label = matches[matches[HIERARCHY_COLUMN] == max_level][CROP_COLUMN].iloc[0]
        matches = matches[matches[CROP_COLUMN] == best_label]

    if YEAR_COLUMN in matches.columns and MONTH_COLUMN in matches.columns:
        matches = matches.copy()
        matches["_sort_key"] = matches[YEAR_COLUMN] * 100 + matches[MONTH_COLUMN]
        matches = matches.sort_values("_sort_key")

    if PRICE_COLUMN not in matches.columns:
        return {"data_points": len(matches), "pct_change": None, "latest_index": None}

    recent = matches.tail(months)
    if len(recent) < 2:
        latest = recent[PRICE_COLUMN].iloc[-1] if len(recent) else None
        return {"data_points": len(matches), "pct_change": None, "latest_index": latest}

    first_val = recent[PRICE_COLUMN].iloc[0]
    last_val = recent[PRICE_COLUMN].iloc[-1]
    pct_change = None
    if first_val not in (None, 0):
        pct_change = round((last_val - first_val) / first_val * 100, 1)

    return {
        "data_points": len(matches),
        "pct_change": pct_change,
        "latest_index": last_val,
    }


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
            parts.append(f"variation de l'indice de prix sur la période récente: {trend['pct_change']}%")
        if trend.get("latest_index") is not None:
            parts.append(f"dernier indice connu (base 100): {trend['latest_index']}")
        parts.append(f"nombre de points de données: {trend['data_points']}")
        trend_block = ", ".join(parts)

    return f"""Culture évaluée : {crop_name}

Données chiffrées calculées :
{trend_block}

Contexte documentaire (marché français) :
{context_block}

Donne une évaluation de rentabilité pour planter cette culture le mois prochain,
en te basant uniquement sur les informations ci-dessus."""


SYSTEM_PROMPT = """Tu es un conseiller agricole qui évalue la rentabilité de cultures
pour le marché français. Réponds UNIQUEMENT avec un objet JSON valide, structuré
exactement ainsi:
{
  "culture": "<nom de la culture>",
  "score": <nombre entre 0 et 10>,
  "tendance_prix": "<hausse|stable|baisse|inconnue>",
  "justification": "<2-3 phrases maximum, en français>",
  "donnees_suffisantes": <true ou false>
}

Règles importantes:
- Les données chiffrées (variation de prix CSV) et le contexte documentaire
  (bulletins de marché) sont deux sources indépendantes. Si l'une des deux
  manque mais que l'autre est riche et pertinente, utilise celle qui est
  disponible - ne mets PAS donnees_suffisantes à false juste parce que les
  chiffres CSV sont absents.
- Mets donnees_suffisantes à false UNIQUEMENT si les deux sources sont vides
  ou non pertinentes (aucune donnée chiffrée ET aucun contexte documentaire
  utilisable pour cette culture spécifique).
- Ne mets jamais un score au-dessus de 3 si donnees_suffisantes est false.
- N'invente jamais de chiffres qui ne sont pas dans les données fournies.
"""


def score_crop(crop_name: str) -> dict:
    """Scores a single crop: retrieval + computed trend -> structured JSON verdict.
    Also returns supporting stats (chunks found, sources, timings) for transparency."""
    t0 = time.perf_counter()
    # Older local indexes (including the bundled one) do not contain the
    # ``doc_type`` metadata field. Filtering on it silently returns no rows,
    # so use the complete market index and let semantic retrieval find the
    # relevant crop passages.
    hits = retrieve(crop_name, top_k=TOP_K_PER_CROP)
    retrieval_time = time.perf_counter() - t0

    trend = compute_price_trend(crop_name)
    user_message = build_crop_prompt(crop_name, hits, trend)

    t1 = time.perf_counter()
    response = complete_chat(
        model=CHAT_MODEL,
        messages=[
            {"role": "system", "content": SYSTEM_PROMPT},
            {"role": "user", "content": user_message},
        ],
        response_format={"type": "json_object"},
        temperature=0.2,
        seed=42,
    )
    generation_time = time.perf_counter() - t1

    raw = response.choices[0].message.content
    try:
        parsed = json.loads(raw)
    except json.JSONDecodeError:
        parsed = {
            "culture": crop_name,
            "score": 0,
            "tendance_prix": "inconnue",
            "justification": "Erreur: réponse du modèle non parsable.",
            "donnees_suffisantes": False,
        }

    # Enrich with stats regardless of what the model returned.
    parsed["stats"] = {
        "chunks_trouves": len(hits),
        "sources": sorted(set(h["metadata"].get("source", "unknown") for h in hits)),
        "avg_rerank_score": (
            round(sum(h.get("rerank_score", 0) for h in hits) / len(hits), 4)
            if hits else None
        ),
        "tendance_csv": trend,  # raw computed trend dict, or None if no CSV match
        "retrieval_time_s": round(retrieval_time, 3),
        "generation_time_s": round(generation_time, 3),
    }
    return parsed


def rank_crops(crops: list, top_n: int = 3) -> dict:
    """
    Main entrypoint. Call this with the list of candidate crops received
    from the upstream agent. Returns the top_n ranked by score (descending)
    plus the full evaluation of every candidate for transparency/logging.
    """
    results = [score_crop(crop) for crop in crops]
    results.sort(key=lambda r: r.get("score", 0), reverse=True)

    return {
        "top": results[:top_n],
        "all_evaluated": results,
    }


if __name__ == "__main__":
    import argparse
    import sys

    parser = argparse.ArgumentParser(
        description="Rank candidate crops using French market data. "
                    "Pass crops as arguments, or pipe a JSON list via stdin."
    )
    parser.add_argument(
        "crops", nargs="*",
        help='Crop names, e.g.: python rank_crops.py banane tomate "pomme de terre" mangue avocat'
    )
    parser.add_argument(
        "--top", type=int, default=3,
        help="How many top crops to return (default: 3)"
    )
    args = parser.parse_args()

    if args.crops:
        crops = args.crops
    elif not sys.stdin.isatty():
        # Allows: echo '["banane","tomate","pomme de terre","mangue","avocat"]' | python rank_crops.py
        crops = json.loads(sys.stdin.read())
    else:
        crops = ["banane", "tomate", "pomme de terre", "mangue", "avocat"]
        print(f"[info] No crops given, using example list: {crops}", file=sys.stderr)

    output = rank_crops(crops, top_n=args.top)
    print(json.dumps(output, indent=2, ensure_ascii=False))
