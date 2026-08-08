"""
Shared helper: given a HAL document ID (the prefix before the first
underscore in filenames produced by scripts/fetch_hal_documents.py,
e.g. "hal-00885981" from "hal-00885981_Management_of_nitrogen...pdf"),
looks up the real document title from HAL's public search API and
constructs its permalink.

hal.science is HAL's unified landing-page domain across all of its
sub-portals (hal-, tel-, dumas-, cirad-, pastel-, medihal-, etc.) — the
URL is always constructible from the ID alone, no lookup needed. Only
the TITLE requires a network call.

Used by:
- scripts/ingest_rag_corpus.py — looked up once per file at ingest time
- backfill_chunk_titles.py — looked up once per already-ingested
  source_document, to retrofit chunks that predate this feature
"""
import re
import httpx
from tenacity import retry, stop_after_attempt, wait_exponential

HAL_SEARCH_URL = "https://api.archives-ouvertes.fr/search/"


def hal_id_from_filename(filename: str) -> str:
    """'hal-00885981_Management_of...pdf' -> 'hal-00885981'"""
    return filename.split("_", 1)[0]


def hal_url(hal_id: str) -> str:
    return f"https://hal.science/{hal_id}"


def _fallback_title(filename: str) -> str:
    """
    Used only if the HAL API lookup fails (network hiccup, record since
    removed, etc.) — reconstructs a readable-ish title from the
    slugified filename. Degraded (accents/truncation already lost at
    fetch time) but still far better than showing a raw chunk UUID.
    """
    hal_id = hal_id_from_filename(filename)
    rest = filename[len(hal_id) + 1:]
    rest = re.sub(r"\.pdf$", "", rest, flags=re.IGNORECASE)
    return rest.replace("_", " ").strip() or hal_id


def offline_fallback_title(filename: str) -> str:
    """
    Public, network-free version of the fallback title logic — safe to
    call from request-serving code (e.g. synthesis_service.py) where a
    live HAL lookup per request would be slow and adds a failure mode.
    Chunks should normally already carry a real title from ingest-time
    lookup or the backfill script; this is only a defensive fallback.
    """
    return _fallback_title(filename)


@retry(stop=stop_after_attempt(3), wait=wait_exponential(min=1, max=8))
def _query_hal_title(hal_id: str) -> str | None:
    # Exact-match lookup by ID: broad q + exact fq, same pattern as
    # fetch_hal_documents.py's proven-working _search_hal(). An earlier
    # version used q="halId_s:{hal_id}" directly — that silently
    # returned zero results for every single document in a live
    # backfill run (100% fallback rate, never surfaced as an error
    # since empty results aren't an exception). fq is HAL's exact-match
    # filter; q's free-text relevance parser was never the right tool
    # for an exact ID lookup. Confirmed working via debug_hal_lookup.py
    # against a real document (numFound: 1, correct title returned).
    params = {"q": "*:*", "fq": f"halId_s:{hal_id}", "wt": "json", "rows": 1, "fl": "title_s"}
    with httpx.Client(timeout=10) as client:
        resp = client.get(HAL_SEARCH_URL, params=params)
        resp.raise_for_status()
        docs = resp.json().get("response", {}).get("docs", [])
        if not docs:
            return None
        title = docs[0].get("title_s")
        return title[0] if isinstance(title, list) and title else title


def lookup_title_and_url(filename: str) -> tuple[str, str, bool]:
    """
    Returns (title, url, is_real_title) for a source_document filename.
    Never raises — falls back to a filename-derived title if the HAL
    lookup fails or returns nothing, since a degraded title is far
    better than blocking an ingest/backfill run over a single document.
    is_real_title tells the caller which case happened, so a failure
    can be reported instead of silently looking identical to success —
    a previous version of this function didn't distinguish the two,
    and every lookup in a live backfill run fell back without any of
    the calling scripts ever printing that fact.
    """
    hal_id = hal_id_from_filename(filename)
    url = hal_url(hal_id)
    try:
        title = _query_hal_title(hal_id)
    except Exception:
        title = None
    if title:
        return (title, url, True)
    return (_fallback_title(filename), url, False)
