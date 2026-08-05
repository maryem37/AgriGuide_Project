"""
Qdrant (Cloud) wrapper used to index every validated Waste entry for
semantic retrieval by the reasoner agent.

One "document" per Waste = a synthesized text blob covering its
description, composition, transformations, and applications, so a single
semantic search can surface the most relevant waste entries for a
free-form user question.
"""
from __future__ import annotations

from typing import Optional

from config.logging_config import get_logger
from config.settings import settings, ensure_directories
from models import Crop, Waste

logger = get_logger(__name__)


def waste_to_document_text(crop: Crop, waste: Waste) -> str:
    """Build the text blob that gets embedded and indexed for a waste entry."""
    parts = [
        f"Crop: {crop.canonical_name or crop.name}",
        f"Scientific name: {crop.scientific_name}" if crop.scientific_name else "",
        f"Waste: {waste.canonical_name or waste.name}",
        f"Category: {waste.category}" if waste.category else "",
        f"Plant part: {waste.plant_part}" if waste.plant_part else "",
        f"Description: {waste.description}" if waste.description else "",
    ]
    if waste.composition:
        comp_str = "; ".join(f"{c.component}: {c.value}{c.unit or ''}" for c in waste.composition)
        parts.append(f"Composition: {comp_str}")
    if waste.transformations:
        trans_str = "; ".join(
            f"{t.input_waste} -> {t.process} -> {t.output_product}" for t in waste.transformations
        )
        parts.append(f"Transformations: {trans_str}")
    if waste.final_products:
        parts.append(f"Final products: {', '.join(waste.final_products)}")
    for label, apps in (
        ("Industrial applications", waste.industrial_applications),
        ("Agricultural applications", waste.agricultural_applications),
        ("Environmental applications", waste.environmental_applications),
    ):
        if apps:
            parts.append(f"{label}: {', '.join(a.name for a in apps)}")
    if waste.advantages:
        parts.append(f"Advantages: {', '.join(waste.advantages)}")
    if waste.limitations:
        parts.append(f"Limitations: {', '.join(waste.limitations)}")
    return "\n".join(p for p in parts if p)


class VectorStoreService:
    """Wraps a Qdrant Cloud collection for Waste documents."""

    def __init__(
        self,
        url: Optional[str] = None,
        api_key: Optional[str] = None,
        collection_name: Optional[str] = None,
    ) -> None:
        ensure_directories()
        self.url = url or settings.qdrant_url
        self.api_key = api_key or settings.qdrant_api_key
        self.collection_name = collection_name or settings.qdrant_collection_name
        self._client = None
        self._collection_ready = False

    def _get_client(self):
        if self._client is None:
            from qdrant_client import QdrantClient

            self._client = QdrantClient(url=self.url, api_key=self.api_key, timeout=30)
        return self._client

    def _ensure_collection(self, vector_size: int) -> None:
        if self._collection_ready:
            return
        from qdrant_client.models import Distance, VectorParams

        client = self._get_client()
        if not client.collection_exists(self.collection_name):
            client.create_collection(
                collection_name=self.collection_name,
                vectors_config=VectorParams(size=vector_size, distance=Distance.COSINE),
            )
        self._collection_ready = True

    def upsert_waste(self, crop: Crop, waste: Waste) -> None:
        from qdrant_client.models import PointStruct

        from services.embedding_service import get_embedding_service

        text = waste_to_document_text(crop, waste)
        embedding = get_embedding_service().embed_one(text)
        self._ensure_collection(len(embedding))
        self._get_client().upsert(
            collection_name=self.collection_name,
            points=[
                PointStruct(
                    id=waste.id,
                    vector=embedding,
                    payload={
                        "document": text,
                        "crop": crop.canonical_name or crop.name,
                        "waste_name": waste.canonical_name or waste.name,
                        "confidence": waste.confidence,
                        "evidence_source": waste.evidence_source.value,
                        "num_references": len(waste.references),
                    },
                )
            ],
        )
        logger.debug("Upserted waste '%s' (crop=%s) into vector store.", waste.name, crop.name)

    def upsert_crop(self, crop: Crop) -> None:
        for waste in crop.wastes:
            self.upsert_waste(crop, waste)

    def query(self, question: str, n_results: int = 6, crop_filter: Optional[str] = None) -> list[dict]:
        from qdrant_client.models import FieldCondition, Filter, MatchValue

        from services.embedding_service import get_embedding_service

        embedding = get_embedding_service().embed_one(question)
        self._ensure_collection(len(embedding))
        query_filter = (
            Filter(must=[FieldCondition(key="crop", match=MatchValue(value=crop_filter))])
            if crop_filter
            else None
        )
        results = self._get_client().query_points(
            collection_name=self.collection_name,
            query=embedding,
            limit=n_results,
            query_filter=query_filter,
            with_payload=True,
        ).points

        hits = []
        for point in results:
            payload = dict(point.payload or {})
            document = payload.pop("document", "")
            hits.append(
                {
                    "id": str(point.id),
                    "document": document,
                    "metadata": payload,
                    "distance": 1.0 - point.score,
                }
            )
        return hits

    def count(self) -> int:
        try:
            client = self._get_client()
            if not client.collection_exists(self.collection_name):
                return 0
            return client.count(collection_name=self.collection_name, exact=True).count
        except Exception:  # noqa: BLE001
            return 0


_vector_store_singleton: Optional[VectorStoreService] = None


def get_vector_store() -> VectorStoreService:
    global _vector_store_singleton
    if _vector_store_singleton is None:
        _vector_store_singleton = VectorStoreService()
    return _vector_store_singleton
