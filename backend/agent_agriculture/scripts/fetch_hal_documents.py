"""
Automates document sourcing from HAL — queries HAL's free public search
API, filters to open-access records that actually have a downloadable
PDF (fileMain_s), and saves them into ./corpus/ so
scripts/ingest_rag_corpus.py can chunk/embed them.

No key, no auth, no cost — HAL's search API is fully public.

Ported as-is from the standalone `agri-advisor-parcelle` prototype. Run
from `backend/agent_agriculture/`:

    python -m scripts.fetch_hal_documents --query "ble tendre fertilisation" \
        --coll INRAE --rows 30 --out ./corpus_ble

    # Broader agronomy sweep across several topics in one run:
    python -m scripts.fetch_hal_documents --query "agronomie irrigation" --coll INRAE --rows 50
"""
import argparse
import re
import time
from pathlib import Path
import httpx
from tenacity import retry, stop_after_attempt, wait_exponential

HAL_SEARCH_URL = "https://api.archives-ouvertes.fr/search/"


def _safe_filename(hal_id: str, title: str) -> str:
    slug = re.sub(r"[^a-zA-Z0-9_-]+", "_", title.strip())[:60]
    return f"{hal_id}_{slug}.pdf"


@retry(stop=stop_after_attempt(3), wait=wait_exponential(min=1, max=8))
def _search_hal(query: str, coll: str | None, rows: int, start: int) -> dict:
    params = {
        "q": query,
        "wt": "json",
        "rows": rows,
        "start": start,
        # fl = fields to return: id, title, PDF link, doc type, date, collection
        "fl": "halId_s,title_s,fileMain_s,docType_s,producedDateY_i,collCode_s",
        "sort": "producedDateY_i desc",
    }
    if coll:
        params["fq"] = f"collCode_s:{coll}"

    with httpx.Client(timeout=15) as client:
        resp = client.get(HAL_SEARCH_URL, params=params)
        resp.raise_for_status()
        return resp.json()


@retry(stop=stop_after_attempt(3), wait=wait_exponential(min=1, max=8))
def _download_pdf(url: str, dest: Path) -> None:
    with httpx.Client(timeout=30, follow_redirects=True) as client:
        resp = client.get(url)
        resp.raise_for_status()
        dest.write_bytes(resp.content)


def fetch_hal_documents(query: str, coll: str | None, rows: int, out_dir: Path) -> int:
    out_dir.mkdir(parents=True, exist_ok=True)
    data = _search_hal(query, coll, rows, start=0)
    docs = data.get("response", {}).get("docs", [])

    downloaded = 0
    skipped_no_pdf = 0

    for doc in docs:
        pdf_url = doc.get("fileMain_s")  # absent when the record has no open full text
        hal_id = doc.get("halId_s", "unknown")
        title = doc.get("title_s", ["untitled"])
        title = title[0] if isinstance(title, list) else title

        if not pdf_url:
            skipped_no_pdf += 1
            continue

        dest = out_dir / _safe_filename(hal_id, title)
        if dest.exists():
            continue  # already fetched in a previous run

        try:
            _download_pdf(pdf_url, dest)
            downloaded += 1
            print(f"Downloaded: {dest.name}")
            time.sleep(0.5)  # be polite to a free public service, no rate-limit stated but avoid hammering it
        except httpx.HTTPError as e:
            print(f"Failed to download {hal_id}: {e}")

    print(f"\nDone. {downloaded} PDFs downloaded, {skipped_no_pdf} records had no open full text.")
    return downloaded


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--query", required=True, help='e.g. "ble tendre fertilisation"')
    ap.add_argument("--coll", default=None, help='HAL collection code, e.g. "INRAE" to restrict to INRAE')
    ap.add_argument("--rows", type=int, default=30, help="max records to fetch (HAL default cap ~1000/request)")
    ap.add_argument("--out", default="./corpus", help="output folder for downloaded PDFs")
    args = ap.parse_args()

    fetch_hal_documents(args.query, args.coll, args.rows, Path(args.out))


if __name__ == "__main__":
    main()
