"""
Lightweight persistent vector store (numpy + JSON metadata).

Avoids chromadb/hnswlib native builds that break on Windows without MSVC.
API is intentionally small: create / add / query / count / exists.
"""

from __future__ import annotations

import json
from pathlib import Path

import numpy as np


class LocalVectorStore:
    def __init__(self, root: str | Path, collection: str = "agri_market_data"):
        self.root = Path(root)
        self.collection = collection
        self.dir = self.root / collection
        self._emb_path = self.dir / "embeddings.npy"
        self._docs_path = self.dir / "documents.jsonl"
        self._meta_path = self.dir / "metadatas.jsonl"
        self._embeddings: np.ndarray | None = None
        self._documents: list[str] | None = None
        self._metadatas: list[dict] | None = None

    def exists(self) -> bool:
        return self._emb_path.exists() and self._docs_path.exists()

    def reset(self) -> None:
        self.dir.mkdir(parents=True, exist_ok=True)
        for p in (self._emb_path, self._docs_path, self._meta_path):
            if p.exists():
                p.unlink()
        self._embeddings = np.zeros((0, 0), dtype=np.float32)
        self._documents = []
        self._metadatas = []

    def _ensure_loaded(self) -> None:
        if self._embeddings is not None:
            return
        if not self.exists():
            raise RuntimeError(
                f"Vector store '{self.collection}' not found in {self.root}. "
                "Run: python -m app.market_intelligence.rag.ingest"
            )
        self._embeddings = np.load(self._emb_path)
        self._documents = [
            json.loads(line)["text"] for line in self._docs_path.read_text(encoding="utf-8").splitlines() if line
        ]
        self._metadatas = [
            json.loads(line) for line in self._meta_path.read_text(encoding="utf-8").splitlines() if line
        ]

    def add(
        self,
        embeddings: list[list[float]],
        documents: list[str],
        metadatas: list[dict],
    ) -> None:
        if not embeddings:
            return
        self.dir.mkdir(parents=True, exist_ok=True)
        batch = np.asarray(embeddings, dtype=np.float32)
        # L2-normalize for cosine via dot product
        norms = np.linalg.norm(batch, axis=1, keepdims=True)
        norms = np.clip(norms, 1e-12, None)
        batch = batch / norms

        if self._emb_path.exists():
            existing = np.load(self._emb_path)
            if existing.size:
                batch = np.vstack([existing, batch])
        np.save(self._emb_path, batch)

        with self._docs_path.open("a", encoding="utf-8") as fdocs, self._meta_path.open(
            "a", encoding="utf-8"
        ) as fmeta:
            for doc, meta in zip(documents, metadatas):
                fdocs.write(json.dumps({"text": doc}, ensure_ascii=False) + "\n")
                fmeta.write(json.dumps(meta, ensure_ascii=False) + "\n")

        self._embeddings = None
        self._documents = None
        self._metadatas = None

    def count(self) -> int:
        if not self.exists():
            return 0
        self._ensure_loaded()
        assert self._documents is not None
        return len(self._documents)

    def query(
        self,
        query_embedding: list[float],
        n_results: int = 20,
        where: dict | None = None,
    ) -> tuple[list[str], list[dict], list[float]]:
        self._ensure_loaded()
        assert self._embeddings is not None and self._documents is not None and self._metadatas is not None

        q = np.asarray(query_embedding, dtype=np.float32)
        q = q / max(float(np.linalg.norm(q)), 1e-12)
        scores = self._embeddings @ q  # cosine similarity

        indices = list(range(len(self._documents)))
        if where:
            indices = [
                i
                for i in indices
                if all(self._metadatas[i].get(k) == v for k, v in where.items())
            ]
            if not indices:
                return [], [], []

        ranked = sorted(indices, key=lambda i: float(scores[i]), reverse=True)[:n_results]
        docs = [self._documents[i] for i in ranked]
        metas = [self._metadatas[i] for i in ranked]
        # Convert similarity to a distance-like value for compatibility
        dists = [float(1.0 - scores[i]) for i in ranked]
        return docs, metas, dists
