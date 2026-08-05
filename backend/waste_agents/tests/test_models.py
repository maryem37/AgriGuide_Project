"""Unit tests for models.py - Waste.merge_with, Crop.upsert_waste, KnowledgeBase.upsert_crop."""
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from models import Composition, Crop, EvidenceSource, KnowledgeBase, Reference, SourceType, Waste


def make_reference(title: str) -> Reference:
    return Reference(source_type=SourceType.ACADEMIC_PAPER, title=title)


def test_waste_merge_keeps_higher_confidence_description() -> None:
    w1 = Waste(name="Rice Husk", canonical_name="Rice Husk", confidence=0.85, description="Old description")
    w2 = Waste(name="Rice Husk", canonical_name="Rice Husk", confidence=0.95, description="New, better description")
    merged = w1.merge_with(w2)
    assert merged.confidence == 0.95
    assert merged.description == "New, better description"


def test_waste_merge_unions_composition_without_duplicates() -> None:
    w1 = Waste(
        name="Rice Husk",
        canonical_name="Rice Husk",
        composition=[Composition(component="Silica", value="20", unit="%")],
    )
    w2 = Waste(
        name="Rice Husk",
        canonical_name="Rice Husk",
        composition=[
            Composition(component="Silica", value="20", unit="%"),
            Composition(component="Cellulose", value="35", unit="%"),
        ],
    )
    merged = w1.merge_with(w2)
    components = {c.component for c in merged.composition}
    assert components == {"Silica", "Cellulose"}


def test_waste_merge_dedupes_references() -> None:
    ref = make_reference("Same Paper")
    w1 = Waste(name="Peel", canonical_name="Peel", references=[ref])
    w2 = Waste(name="Peel", canonical_name="Peel", references=[ref])
    merged = w1.merge_with(w2)
    assert len(merged.references) == 1


def test_crop_upsert_waste_merges_existing() -> None:
    crop = Crop(name="Banana", canonical_name="Banana")
    crop.upsert_waste(Waste(name="Peel", canonical_name="Peel", confidence=0.8))
    crop.upsert_waste(Waste(name="Peel", canonical_name="Peel", confidence=0.9, description="better"))
    assert len(crop.wastes) == 1
    assert crop.wastes[0].confidence == 0.9


def test_knowledge_base_upsert_crop_merges_by_name() -> None:
    kb = KnowledgeBase()
    kb.upsert_crop(Crop(name="Rice", canonical_name="Rice", wastes=[Waste(name="Husk", canonical_name="Husk")]))
    kb.upsert_crop(Crop(name="Rice", canonical_name="Rice", wastes=[Waste(name="Straw", canonical_name="Straw")]))
    assert len(kb.crops) == 1
    assert len(kb.crops[0].wastes) == 2


def test_knowledge_base_stats() -> None:
    kb = KnowledgeBase()
    crop = Crop(name="Rice", canonical_name="Rice")
    waste = Waste(name="Husk", canonical_name="Husk", final_products=["Biochar"])
    crop.wastes.append(waste)
    kb.crops.append(crop)
    stats = kb.stats()
    assert stats["num_crops"] == 1
    assert stats["num_wastes"] == 1
    assert stats["num_products"] == 1
