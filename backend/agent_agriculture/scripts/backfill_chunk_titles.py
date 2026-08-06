"""
One-time backfill: adds "title" and "url" metadata to every chunk
already in the Chroma store — needed because those chunks were indexed
before this feature existed and only carry source_document, crop,
region, topic. New ingests (via scripts/ingest_rag_corpus.py) already
set title/url at index time; this script catches up everything ingested
before that change.

Groups chunks by source_document (so each real document is only looked
up once on HAL, not once per chunk), fetches the real title + permalink
via app.hal_title_lookup, then updates each chunk's metadata in place —
merging title/url in without touching crop/region/topic.

Ported as-is from the standalone `agri-advisor-parcelle` prototype. Run
from `backend/agent_agriculture/`:

    python -m scripts.backfill_chunk_titles            # do it
    python -m scripts.backfill_chunk_titles --dry-run  # just show what would change
"""
import argparse
from app.services.rag_service import _collection
from app.hal_title_lookup import lookup_title_and_url


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--dry-run", action="store_true", help="Show what would be updated without writing")
    ap.add_argument(
        "--force", action="store_true",
        help="Re-lookup and overwrite every document's title, even ones that already have one "
             "(needed to retry documents that got a fallback title recorded from a failed lookup)",
    )
    args = ap.parse_args()

    all_chunks = _collection.get(limit=100000)  # metadatas + ids for everything in the store
    ids = all_chunks.get("ids", [])
    metadatas = all_chunks.get("metadatas", [])
    if not ids:
        print("Store is empty — nothing to backfill.")
        return

    # Group chunk indices by source_document, skipping any that already
    # have a title (so re-running this script is cheap/idempotent).
    by_source: dict[str, list[int]] = {}
    for idx, meta in enumerate(metadatas):
        if meta.get("title") and not args.force:
            continue
        src = meta.get("source_document")
        if not src:
            continue
        by_source.setdefault(src, []).append(idx)

    if not by_source:
        print("Every chunk already has a title — nothing to backfill.")
        return

    print(f"{len(by_source)} document(s) need a title/url lookup ({sum(len(v) for v in by_source.values())} chunks total).\n")

    updated_docs, updated_chunks, real_count, fallback_count = 0, 0, 0, 0
    for source_document, indices in sorted(by_source.items()):
        title, url, is_real = lookup_title_and_url(source_document)
        status = "REAL" if is_real else "FALLBACK (HAL lookup failed/empty)"
        print(f"  [{status}] {source_document}\n    -> title: {title}\n    -> url:   {url}")
        if is_real:
            real_count += 1
        else:
            fallback_count += 1

        if args.dry_run:
            continue

        update_ids = [ids[i] for i in indices]
        update_metadatas = []
        for i in indices:
            merged = dict(metadatas[i])
            merged["title"] = title
            merged["url"] = url
            update_metadatas.append(merged)

        _collection.update(ids=update_ids, metadatas=update_metadatas)
        updated_docs += 1
        updated_chunks += len(indices)

    print(f"\nTitle lookup results: {real_count} real, {fallback_count} fallback.")
    if fallback_count and real_count == 0:
        print(
            "⚠️  ALL lookups fell back — this points to a systemic problem (network, HAL API "
            "change, or a bug in the query), not per-document issues. Worth investigating before "
            "trusting these titles."
        )
    elif fallback_count:
        print(f"⚠️  {fallback_count} document(s) got a degraded filename-derived title — HAL had no "
              f"match or the record may since have been removed/renamed. Safe to leave as-is or "
              f"re-run later.")

    if args.dry_run:
        print(f"\n[DRY RUN] Would update {len(by_source)} document(s). Re-run without --dry-run to apply.")
    else:
        print(f"\nDone. Updated {updated_docs} document(s), {updated_chunks} chunk(s).")


if __name__ == "__main__":
    main()
