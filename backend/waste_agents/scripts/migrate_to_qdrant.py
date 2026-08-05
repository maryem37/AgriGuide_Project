"""
One-off migration: rebuild the Qdrant vector store index from the
canonical knowledge base JSON (knowledge/canonical_knowledge.json).

The vector store only ever holds a *derived* index (embeddings + a
denormalized text blob per waste) -- it is never the source of truth.
Re-embedding every waste from the canonical JSON therefore reproduces the
same index on Qdrant with zero data loss, without needing to touch the
old ChromaDB files at all.

Usage:
    python scripts/migrate_to_qdrant.py

Requires QDRANT_URL and QDRANT_API_KEY to be set in .env (see
.env.example -- create a free cluster at https://cloud.qdrant.io first).
"""
from __future__ import annotations

import sys
import time
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from config.settings import settings
from services.storage_service import get_storage_service
from services.vector_store_service import VectorStoreService


def main() -> int:
    if not settings.qdrant_url or not settings.qdrant_api_key:
        print("QDRANT_URL and QDRANT_API_KEY must be set in .env before running this migration.")
        return 1

    kb = get_storage_service().load()
    total_wastes = sum(len(crop.wastes) for crop in kb.crops)
    if total_wastes == 0:
        print("Knowledge base is empty (no crops/wastes found) -- nothing to migrate.")
        return 0

    print(f"Migrating {total_wastes} waste entries across {len(kb.crops)} crops to Qdrant...")
    vector_store = VectorStoreService()

    done = 0
    start = time.time()
    for crop in kb.crops:
        for waste in crop.wastes:
            for attempt in range(3):
                try:
                    vector_store.upsert_waste(crop, waste)
                    break
                except Exception as e:  # noqa: BLE001
                    if attempt == 2:
                        raise
                    print(f"  retrying after transient error: {e}")
                    time.sleep(3)
            done += 1
            print(f"  [{done}/{total_wastes}] {crop.name} / {waste.canonical_name or waste.name}")

    elapsed = time.time() - start
    indexed = vector_store.count()
    print(f"\nDone in {elapsed:.1f}s. Qdrant collection '{vector_store.collection_name}' now has {indexed} points.")
    if indexed != total_wastes:
        print(
            f"WARNING: expected {total_wastes} points but collection reports {indexed}. "
            "Check for duplicate waste IDs in the knowledge base."
        )
        return 1
    return 0


if __name__ == "__main__":
    sys.exit(main())
