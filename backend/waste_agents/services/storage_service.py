"""
Storage service for the canonical knowledge JSON file.

Provides atomic, thread-safe-ish read/write of the KnowledgeBase model to
disk. Uses a write-to-temp-then-rename pattern to avoid corrupting the
file if the process is interrupted mid-write.
"""
from __future__ import annotations

import os
import tempfile
import threading
from pathlib import Path
from typing import Optional

from config.logging_config import get_logger
from config.settings import settings, ensure_directories
from models import KnowledgeBase

logger = get_logger(__name__)

_lock = threading.Lock()


class StorageService:
    """Handles persistence of the canonical KnowledgeBase to JSON."""

    def __init__(self, path: Optional[str] = None) -> None:
        ensure_directories()
        self.path = Path(path or settings.canonical_knowledge_path)

    def load(self) -> KnowledgeBase:
        with _lock:
            if not self.path.exists():
                logger.info("No existing knowledge base found at %s, starting empty.", self.path)
                return KnowledgeBase()
            try:
                raw = self.path.read_text(encoding="utf-8")
                return KnowledgeBase.model_validate_json(raw)
            except Exception as e:  # noqa: BLE001
                logger.error("Failed to load knowledge base from %s: %s. Starting empty.", self.path, e)
                return KnowledgeBase()

    def save(self, kb: KnowledgeBase) -> None:
        with _lock:
            self.path.parent.mkdir(parents=True, exist_ok=True)
            fd, tmp_path = tempfile.mkstemp(dir=str(self.path.parent), suffix=".tmp")
            try:
                with os.fdopen(fd, "w", encoding="utf-8") as f:
                    f.write(kb.model_dump_json(indent=2))
                os.replace(tmp_path, self.path)
                logger.info("Knowledge base saved to %s (%d crops).", self.path, len(kb.crops))
            except Exception:
                if os.path.exists(tmp_path):
                    os.remove(tmp_path)
                raise


_storage_singleton: Optional[StorageService] = None


def get_storage_service() -> StorageService:
    global _storage_singleton
    if _storage_singleton is None:
        _storage_singleton = StorageService()
    return _storage_singleton
