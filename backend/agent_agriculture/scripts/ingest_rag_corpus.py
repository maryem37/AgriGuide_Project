"""
Run manually / offline to populate the RAG store from local files.
Point --input at a folder of PDFs/HTML/markdown pulled from HAL,
FranceAgriMer, FAO, etc.

Ported from the standalone `agri-advisor-parcelle` prototype (import
paths updated to the `app.*` package layout). Run from
`backend/agent_agriculture/`:

    python -m scripts.ingest_rag_corpus --input ./corpus_ble --crop ble_tendre --region "Ile-de-France" --topic fertilisation
"""
import argparse
import mimetypes
from pathlib import Path
import app._compat_shims  # noqa: F401 — must run before the unstructured import below
from unstructured.partition.auto import partition
from app.services.rag_service import chunk_document, index_chunks, _collection
from app.taxonomy import normalize_crop
from app.hal_title_lookup import lookup_title_and_url

# Files larger than this are skipped rather than risking a multi-hour
# hang on pdfminer parsing a huge scanned/image-heavy PDF. Adjust up if
# you specifically need a large file included.
_MAX_FILE_SIZE_MB = 25

# `unstructured`'s auto-partitioner falls back to `python-magic` (a wrapper
# around the libmagic C library) whenever no content-type is given — Windows
# has no libmagic by default, so that fallback hard-crashes with
# `ImportError: failed to find libmagic` instead of degrading gracefully.
# Passing an explicit content-type (for the file types this project actually
# downloads — see fetch_hal_documents.py, always PDFs) skips libmagic
# entirely; only truly unknown extensions still risk hitting it.
_EXTENSION_CONTENT_TYPES = {
    ".pdf": "application/pdf",
    ".html": "text/html",
    ".htm": "text/html",
    ".md": "text/markdown",
    ".markdown": "text/markdown",
    ".txt": "text/plain",
}


def extract_text(path: Path) -> str:
    content_type = _EXTENSION_CONTENT_TYPES.get(path.suffix.lower()) or mimetypes.guess_type(str(path))[0]
    elements = partition(filename=str(path), content_type=content_type)
    return "\n\n".join(str(e) for e in elements)


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--input", required=True)
    ap.add_argument("--crop", default="")
    ap.add_argument("--region", default="")
    ap.add_argument("--topic", default="")
    ap.add_argument(
        "--max-size-mb", type=float, default=_MAX_FILE_SIZE_MB,
        help="Skip files larger than this (MB) to avoid pdfminer hangs on huge scanned PDFs",
    )
    ap.add_argument(
        "--force", action="store_true",
        help="Re-index a file even if chunks from it are already in the store "
             "(default: skip already-indexed files to avoid duplicates)",
    )
    args = ap.parse_args()

    folder = Path(args.input)
    if not folder.exists():
        print(f"[ATTENTION] Input folder does not exist: {folder}")
        return
    all_files = [p for p in sorted(folder.glob("**/*")) if p.is_file()]
    if not all_files:
        print(
            f"[ATTENTION] No files found in {folder} — nothing to ingest. "
            f"If this came from fetch_hal_documents.py, check its output "
            f"for '0 PDFs downloaded' before re-running this step."
        )
        return

    skipped, failed, succeeded, already_indexed = [], [], [], []

    for path in all_files:
        size_mb = path.stat().st_size / (1024 * 1024)
        if size_mb > args.max_size_mb:
            print(f"[SKIP] Skipping {path.name} ({size_mb:.1f} MB > {args.max_size_mb} MB limit)")
            skipped.append(path.name)
            continue

        if not args.force:
            existing = _collection.get(where={"source_document": path.name}, limit=1)
            if existing["ids"]:
                print(f"[SKIP] {path.name} already indexed — skipping (use --force to re-index)")
                already_indexed.append(path.name)
                continue

        try:
            title, url, is_real = lookup_title_and_url(path.name)
            text = extract_text(path)
            chunks = chunk_document(
                text,
                source_document=path.name,
                metadata_defaults={
                    "crop": normalize_crop(args.crop) if args.crop else "",
                    "region": args.region,
                    "topic": args.topic,
                    "title": title,
                    "url": url,
                },
            )
            index_chunks(chunks)
            title_status = "" if is_real else "  [FALLBACK TITLE - HAL lookup failed/empty]"
            print(f"Indexed {len(chunks)} chunks from {path.name}  (title: {title}){title_status}")
            succeeded.append(path.name)
        except Exception as e:
            print(f"[ERREUR] Failed on {path.name}: {e}")
            failed.append(path.name)
            continue  # never let one bad file kill the whole run

    print(
        f"\nDone. {len(succeeded)} indexed, {len(already_indexed)} already indexed (skipped), "
        f"{len(skipped)} skipped (too large), {len(failed)} failed (parse errors)."
    )
    if skipped:
        print("Skipped (too large):", ", ".join(skipped))
    if failed:
        print("Failed (parse error):", ", ".join(failed))


if __name__ == "__main__":
    main()
