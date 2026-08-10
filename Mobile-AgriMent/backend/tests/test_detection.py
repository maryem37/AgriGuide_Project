import pytest
from unittest.mock import AsyncMock, MagicMock
from config.settings import get_settings
from services.detection_service import DetectionService
from schemas.detection import DetectionResult

@pytest.mark.asyncio
async def test_create_detection():
    db = AsyncMock()
    db.add = MagicMock()
    db.add_all = MagicMock()
    db.commit = AsyncMock()
    service = DetectionService(db)

    result = DetectionResult(
        species="Test Insect",
        scientific_name="Testus Insectus",
        confidence=0.9,
        risk_level="low",
        description="Test description",
        recommendation="Test recommendation"
    )

    detection = await service.create_detection(
        farmer_id="user-123",
        result=result,
        image_path="test.jpg",
        region="Occitanie"
    )

    assert detection.species == "Test Insect"
    assert db.add.called
    assert db.commit.called

@pytest.mark.asyncio
async def test_notify_region_includes_reporting_farmer_when_requested():
    db = AsyncMock()
    db.add = MagicMock()
    db.add_all = MagicMock()
    db.commit = AsyncMock()

    result = MagicMock()
    result.scalars.return_value.all.return_value = []
    db.execute.return_value = result

    service = DetectionService(db)

    detection = MagicMock(id="detection-1", species="Test Insect", region="Occitanie", risk="high")
    notified = await service.notify_region(
        detection,
        reporting_farmer_id="farmer-1",
        include_reporter=True,
    )

    assert notified == 1
    assert db.add_all.called
    assert db.commit.called
