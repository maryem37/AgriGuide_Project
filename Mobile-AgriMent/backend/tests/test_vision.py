import pytest
from services.vision_service import VisionService

def test_parse_response_with_markdown():
    service = VisionService()
    content = """
Here is the analysis:
```json
{
  "species": "Ladybug",
  "scientific_name": "Coccinellidae",
  "confidence": 0.95,
  "risk_level": "low",
  "description": "Beneficial insect",
  "recommendation": "Do nothing"
}
```
Hope this helps!
"""
    result = service._parse_response(content)
    assert result.species == "Ladybug"
    assert result.confidence == 0.95
    assert result.risk_level == "low"

def test_parse_response_direct_json():
    service = VisionService()
    content = '{"species": "Aphid", "scientific_name": "Aphidoidea", "confidence": 0.8, "risk_level": "medium", "description": "Pest", "recommendation": "Spray"}'
    result = service._parse_response(content)
    assert result.species == "Aphid"
    assert result.confidence == 0.8
    assert result.risk_level == "medium"

def test_parse_response_invalid():
    service = VisionService()
    content = "This is not json at all"
    with pytest.raises(ValueError, match="Could not parse analysis result"):
        service._parse_response(content)
