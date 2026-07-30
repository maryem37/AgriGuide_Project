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
from pathlib import Path
from unstructured.partition.auto import partition
from app.services.rag_service import chunk_document, index_chunks, _collection
from app.taxonomy import normalize_crop

# Files larger than this are skipped rather than risking a multi-hour
# hang on pdfminer parsing a huge scanned/image-heavy PDF. Adjust up if
# you specifically need a large file included.
_MAX_FILE_SIZE_MB = 25


def extract_text(path: Path) -> str:
    elements = partition(filename=str(path))
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
        print(f"⚠️  Input folder does not exist: {folder}")
        return
    all_files = [p for p in sorted(folder.glob("**/*")) if p.is_file()]
    if not all_files:
        print(
            f"⚠️  No files found in {folder} — nothing to ingest. "
            f"If this came from fetch_hal_documents.py, check its output "
            f"for '0 PDFs downloaded' before re-running this step."
        )
        return

    skipped, failed, succeeded, already_indexed = [], [], [], []

    for path in all_files:
        size_mb = path.stat().st_size / (1024 * 1024)
        if size_mb > args.max_size_mb:
            print(f"⏭️  Skipping {path.name} ({size_mb:.1f} MB > {args.max_size_mb} MB limit)")
            skipped.append(path.name)
            continue

        if not args.force:
            existing = _collection.get(where={"source_document": path.name}, limit=1)
            if existing["ids"]:
                print(f"⏭️  {path.name} already indexed — skipping (use --force to re-index)")
                already_indexed.append(path.name)
                continue

        try:
            text = extract_text(path)
            chunks = chunk_document(
                text,
                source_document=path.name,
                metadata_defaults={
                    "crop": normalize_crop(args.crop) if args.crop else "",
                    "region": args.region,
                    "topic": args.topic,
                },
            )
            index_chunks(chunks)
            print(f"Indexed {len(chunks)} chunks from {path.name}")
            succeeded.append(path.name)
        except Exception as e:
            print(f"❌ Failed on {path.name}: {e}")
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
