"""
Unit tests for text_utils.singularize().

Naive "-s" stripping mangles words that end in "s" without being plural
("asparagus" -> "asparagu"). Several of these are crop or final-product
names this project handles directly (Citrus, Asparagus, Molasses), so a
mangled form becomes a database key nothing ever matches again.
"""
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))


def test_words_ending_in_s_that_are_not_plurals_survive() -> None:
    """Naive "-s" stripping mangles these into non-words ("asparagus" ->
    "asparagu"), and several are crop or residue names this project
    handles directly."""
    from text_utils import singularize

    for word in ("asparagus", "citrus", "molasses", "bagasse", "grass", "species"):
        assert singularize(word) == word, word


def test_real_plurals_are_still_singularized() -> None:
    from text_utils import singularize

    assert singularize("Tomatoes") == "tomato"
    assert singularize("Cherries") == "cherry"
    assert singularize("Leaves") == "leaf"
    assert singularize("Bunches") == "bunch"
    assert singularize("Peaches") == "peach"
