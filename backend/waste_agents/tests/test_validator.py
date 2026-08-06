"""
Unit tests for agents/validator.py.

These tests are pure-Python (no API calls) and cover the deterministic
safety net: crop-vs-waste discrimination, confidence floor enforcement,
normalization, and deduplication.
"""
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

import pytest

from agents.validator import ValidationError, ValidatorAgent
from models import EvidenceSource, ExtractionResult, ExtractionStatus, Transformation, Waste


@pytest.fixture
def validator() -> ValidatorAgent:
    return ValidatorAgent()


def make_waste(name: str, confidence: float = 0.9, canonical_name: str = "", description: str = "") -> Waste:
    return Waste(
        name=name,
        canonical_name=canonical_name or name,
        confidence=confidence,
        evidence_source=EvidenceSource.DOCUMENT,
        description=description or f"{name} is a documented agricultural byproduct with known valorization uses.",
    )


def test_rejects_plant_part_as_crop(validator: ValidatorAgent) -> None:
    result = ExtractionResult(
        crop="Husk",
        status=ExtractionStatus.SUCCESS,
        wastes=[make_waste("Rice husk")],
    )
    with pytest.raises(ValidationError):
        validator.validate_and_normalize(result)


def test_accepts_valid_crop(validator: ValidatorAgent) -> None:
    result = ExtractionResult(
        crop="Rice",
        status=ExtractionStatus.SUCCESS,
        wastes=[make_waste("Rice Husk")],
    )
    cleaned = validator.validate_and_normalize(result)
    assert cleaned.crop == "Rice"
    assert len(cleaned.wastes) == 1


def test_waste_identical_to_crop_name_is_rejected(validator: ValidatorAgent) -> None:
    result = ExtractionResult(
        crop="Tomato",
        status=ExtractionStatus.SUCCESS,
        wastes=[make_waste("Tomato"), make_waste("Tomato pomace")],
    )
    cleaned = validator.validate_and_normalize(result)
    names = [w.name for w in cleaned.wastes]
    assert "Tomato" not in names
    assert "Tomato pomace" in names


def test_low_confidence_document_waste_is_rejected(validator: ValidatorAgent) -> None:
    result = ExtractionResult(
        crop="Banana",
        status=ExtractionStatus.SUCCESS,
        wastes=[make_waste("Banana peel", confidence=0.5)],  # below 0.80 floor
    )
    cleaned = validator.validate_and_normalize(result)
    assert len(cleaned.wastes) == 0


def test_synonym_normalization(validator: ValidatorAgent) -> None:
    result = ExtractionResult(
        crop="Maize",
        status=ExtractionStatus.SUCCESS,
        wastes=[make_waste("Corn stover", canonical_name="Corn Stover")],
    )
    cleaned = validator.validate_and_normalize(result)
    assert cleaned.wastes[0].canonical_name == "Maize Stover"


def test_deduplication_merges_wastes(validator: ValidatorAgent) -> None:
    result = ExtractionResult(
        crop="Coconut",
        status=ExtractionStatus.SUCCESS,
        wastes=[
            make_waste("Coconut Shell", canonical_name="Coconut Shell", confidence=0.85),
            make_waste("Coconut shell", canonical_name="Coconut Shell", confidence=0.95),
        ],
    )
    cleaned = validator.validate_and_normalize(result)
    assert len(cleaned.wastes) == 1
    assert cleaned.wastes[0].confidence == 0.95


def test_unknown_status_passes_through_unchanged(validator: ValidatorAgent) -> None:
    result = ExtractionResult(status=ExtractionStatus.UNKNOWN, crop="")
    cleaned = validator.validate_and_normalize(result)
    assert cleaned.status == ExtractionStatus.UNKNOWN
    assert cleaned.wastes == []


def test_rejects_low_content_name_only_entries(validator: ValidatorAgent) -> None:
    result = ExtractionResult(
        crop="Rice",
        status=ExtractionStatus.SUCCESS,
        wastes=[
            make_waste("Husk", description="husk"),
            make_waste("Rice bran", description="Rice bran is rich in oil and used for animal feed and biodiesel."),
        ],
    )
    cleaned = validator.validate_and_normalize(result)
    names = [w.canonical_name for w in cleaned.wastes]
    assert "Husk" not in names
    assert "Rice Bran" in names


def test_rejects_product_state_terms(validator: ValidatorAgent) -> None:
    result = ExtractionResult(
        crop="Rice",
        status=ExtractionStatus.SUCCESS,
        wastes=[
            make_waste("Non-harvested paddy"),
            make_waste("Half fill grains"),
            make_waste("Dead grains"),
            make_waste("Low-quality paddy"),
            make_waste("Rotten rice"),
            make_waste("Processed rice"),
            make_waste("Cooked rice"),
            make_waste("Expired rice"),
            make_waste("Rice husk"),
        ],
    )
    cleaned = validator.validate_and_normalize(result)
    names = [w.canonical_name for w in cleaned.wastes]
    assert names == ["Rice Husk"]


def test_straw_not_falsely_flagged_as_product_state(validator: ValidatorAgent) -> None:
    result = ExtractionResult(
        crop="Rice",
        status=ExtractionStatus.SUCCESS,
        wastes=[make_waste("Rice Straw")],
    )
    cleaned = validator.validate_and_normalize(result)
    names = [w.name for w in cleaned.wastes]
    assert "Rice Straw" in names


def test_generic_plant_part_merges_with_crop_prefixed_form(validator: ValidatorAgent) -> None:
    result = ExtractionResult(
        crop="Rice",
        status=ExtractionStatus.SUCCESS,
        wastes=[
            make_waste("Rice husk"),
            Waste(
                name="Husk",
                canonical_name="Husk",
                confidence=0.9,
                evidence_source=EvidenceSource.DOCUMENT,
                description="husk",
                transformations=[
                    Transformation(input_waste="Husk", process="Pyrolysis", output_product="Biochar")
                ],
            ),
        ],
    )
    cleaned = validator.validate_and_normalize(result)
    assert len(cleaned.wastes) == 1


def test_canonicalize_collapses_plural_prefix_and_synonym_variants(
    validator: ValidatorAgent,
) -> None:
    """Regression test for the banana duplication bug: singular/plural,
    bare/crop-prefixed, and skin/peel variants extracted from different
    sources must all collapse to one canonical name per real waste."""
    variants_by_expected = {
        "Banana Pseudostem": ["Pseudostem", "Banana pseudostem", "Banana pseudostems"],
        "Banana Leaf": ["Leaves", "Banana leaves"],
        "Banana Peel": ["Peels", "Banana peel", "Banana skin", "Banana skins"],
        "Banana Stem": ["Banana stem", "Banana stems"],
        "Banana Inflorescence": [
            "Inflorescence",
            "Banana inflorescence",
            "Banana inflorescences",
        ],
    }
    for expected, variants in variants_by_expected.items():
        resolved = {validator._canonicalize(v, "Banana") for v in variants}
        assert resolved == {expected}, f"{variants} -> {resolved}, expected {expected}"


def test_hull_husk_and_meal_oilcake_variants_merge(validator: ValidatorAgent) -> None:
    """Regression test for the sunflower duplication bug: in agronomy
    'hull' and 'husk' name the same seed covering, and 'meal' and
    'oilcake' the same oil-extraction residue. Compound forms like
    'seed hulls' must reduce to their head noun too."""
    assert (
        validator._canonicalize("Sunflower seed hulls", "Sunflower")
        == validator._canonicalize("Sunflower Hull", "Sunflower")
        == validator._canonicalize("Sunflower Husk", "Sunflower")
        == "Sunflower Husk"
    )
    assert (
        validator._canonicalize("Sunflower oilcake", "Sunflower")
        == validator._canonicalize("Sunflower meal", "Sunflower")
        == "Sunflower Meal"
    )


def test_husk_and_shell_stay_distinct(validator: ValidatorAgent) -> None:
    """For coconut and tree nuts the fibrous husk and the hard shell are
    genuinely different residues, so 'shell' must NOT be folded into
    'husk' even though 'hull' is."""
    assert validator._canonicalize("Coconut husk", "Coconut") == "Coconut Husk"
    assert validator._canonicalize("Coconut shell", "Coconut") == "Coconut Shell"


def test_rejects_generic_catch_all_labels(validator: ValidatorAgent) -> None:
    """Regression test: aggregated catch-all buckets carry no information
    and must be dropped, while specific residues survive."""
    result = ExtractionResult(
        crop="Sunflower",
        status=ExtractionStatus.SUCCESS,
        wastes=[
            make_waste("Other by-products"),
            make_waste("Biomass"),
            make_waste("Crop residue"),
            make_waste("Sunflower Stalk"),
        ],
    )
    cleaned = validator.validate_and_normalize(result)
    names = [w.name for w in cleaned.wastes]
    assert names == ["Sunflower Stalk"]


def test_multiword_part_not_flattened_to_head_noun(validator: ValidatorAgent) -> None:
    """'Fruit stalk' is a distinct part in its own right and must not be
    collapsed to plain 'stalk' by the head-noun reduction rule."""
    assert validator._canonicalize("Banana fruit stalk", "Banana") == "Banana Fruit Stalk"
    assert validator._canonicalize("Banana stalk", "Banana") == "Banana Stalk"


def test_milling_fractions_merge_with_their_crop_prefixed_form(validator: ValidatorAgent) -> None:
    """Regression test: 'Germ' and 'Wheat Germ' name the same milling
    fraction and must collapse into one entity."""
    assert (
        validator._canonicalize("Germ", "Wheat")
        == validator._canonicalize("Wheat germ", "Wheat")
        == "Wheat Germ"
    )


def test_rejects_form_factors_that_name_no_plant_part(validator: ValidatorAgent) -> None:
    """'Powders' describes how something was milled, not which part of the
    plant it came from."""
    result = ExtractionResult(
        crop="Wheat",
        status=ExtractionStatus.SUCCESS,
        wastes=[make_waste("Powders"), make_waste("Wheat Bran")],
    )
    cleaned = validator.validate_and_normalize(result)
    assert [w.canonical_name for w in cleaned.wastes] == ["Wheat Bran"]


def test_form_factor_survives_when_qualified_by_a_real_plant_part(validator: ValidatorAgent) -> None:
    """'Bran powder' is still bran, just milled fine -- unlike a bare
    'Powders' it must not be rejected."""
    result = ExtractionResult(
        crop="Wheat",
        status=ExtractionStatus.SUCCESS,
        wastes=[make_waste("Bran powder")],
    )
    cleaned = validator.validate_and_normalize(result)
    assert len(cleaned.wastes) == 1








def test_crop_plural_and_singular_resolve_to_one_crop(validator: ValidatorAgent) -> None:
    """Sources name the same crop either way ("Tomato" / "Tomatoes"). If
    they don't converge, the wastes split across two crop entries and the
    UI finds neither complete."""

    def crop_of(name: str) -> str:
        result = ExtractionResult(
            crop=name,
            status=ExtractionStatus.SUCCESS,
            wastes=[make_waste(f"{name} Peel")],
        )
        return validator.validate_and_normalize(result).crop

    for plural, singular in [
        ("Tomatoes", "Tomato"),
        ("Apples", "Apple"),
        ("Potatoes", "Potato"),
        ("Cherries", "Cherry"),
        ("Mangoes", "Mango"),
        ("Peaches", "Peach"),
    ]:
        assert crop_of(plural) == crop_of(singular) == singular, plural
