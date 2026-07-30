"""
One-off cleanup: removes exact-duplicate chunks (identical source_document +
identical text) from the Chroma collection. Needed because past runs of
ingest_rag_corpus.py had no idempotency check, so re-running it on an
already-indexed folder silently added duplicate copies under new IDs.

Usage:
    python dedupe_chroma.py            # dry run, just reports what it would remove
    python dedupe_chroma.py --apply    # actually deletes the duplicates
"""
import argparse
import chromadb
from chromadb.config import Settings as ChromaSettings
from config import settings


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--apply", action="store_true", help="Actually delete duplicates (default: dry run)")
    args = parser.parse_args()

    client = chromadb.PersistentClient(
        path=settings.chroma_persist_dir,
        settings=ChromaSettings(anonymized_telemetry=False),
    )
    collection = client.get_or_create_collection(settings.chroma_collection)

    total = collection.count()
    print(f"Scanning {total} chunks...")

    batch_size = 1000
    seen = {}  # (source_document, text) -> id kept
    duplicate_ids = []

    offset = 0
    while offset < total:
        batch = collection.get(limit=batch_size, offset=offset, include=["documents", "metadatas"])
        for id_, doc, meta in zip(batch["ids"], batch["documents"], batch["metadatas"]):
            key = (meta.get("source_document", ""), doc)
            if key in seen:
                duplicate_ids.append(id_)
            else:
                seen[key] = id_
        offset += batch_size

    print(f"Found {len(duplicate_ids)} duplicate chunk(s) out of {total} total.")
    if not duplicate_ids:
        print("Nothing to clean up.")
        return

    if args.apply:
        for i in range(0, len(duplicate_ids), batch_size):
            collection.delete(ids=duplicate_ids[i : i + batch_size])
        print(f"Deleted {len(duplicate_ids)} duplicate chunk(s). Remaining: {collection.count()}")
    else:
        print("Dry run only — re-run with --apply to actually delete these.")


if __name__ == "__main__":
    main()
