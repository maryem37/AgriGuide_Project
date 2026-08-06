"""
Regression tests for the Waste model's own data-quality coercion
(models.py).

The model sometimes wraps a plain string in an object
({"name": ..., "description": ..., "confidence": ...}), which previously
leaked raw Python dicts into the UI. The same bug resurfaced three times
in three different fields (chemical_properties, then advantages, then
final_products) because each fix lived in the extractor instead of at the
Pydantic boundary every Waste passes through. The coercion now lives on
the model itself, so it holds regardless of which code path builds a
Waste.
"""
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))


def test_model_itself_rejects_dict_shaped_list_items() -> None:
    """The coercion lives on the model, not the extractor, so it holds even
    for wastes built by other code paths. Fixing this per-field in the
    extractor is what let the same bug resurface three times: first in
    chemical_properties, then advantages, then final_products."""
    from models import Waste

    waste = Waste(
        name="Tomato Peel",
        final_products=["Pectin", {"name": "Beef patties", "description": "long prose", "confidence": 0.95}],
        advantages=[{"description": "Decreases electricity consumption."}],
        limitations=["Plain string", {"name": "Blockage risk"}],
        chemical_properties={"biodegradability": {"value": "biodegradable", "confidence": 0.95}},
        physical_properties={"traits": ["flexible", "light"]},
    )

    assert waste.final_products == ["Pectin", "Beef patties"]
    assert waste.advantages == ["Decreases electricity consumption."]
    assert waste.limitations == ["Plain string", "Blockage risk"]
    assert waste.chemical_properties == {"biodegradability": "biodegradable"}
    assert waste.physical_properties == {"traits": "flexible, light"}

    everything = waste.final_products + waste.advantages + waste.limitations
    assert not any("{" in item for item in everything)
