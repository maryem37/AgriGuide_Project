import logging
from datetime import datetime, timezone
from types import SimpleNamespace

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from models.detection import Detection
from models.farmer import Farmer
from models.notification import Notification
from schemas.detection import DetectionResult, DetectionResponse

logger = logging.getLogger(__name__)


class DetectionService:
    def __init__(self, db: AsyncSession):
        self.db = db

    async def create_detection(
        self,
        farmer_id: str,
        result: DetectionResult,
        image_path: str,
        region: str,
        latitude: float | None = None,
        longitude: float | None = None,
    ) -> Detection:
        detection = Detection(
            farmer_id=farmer_id,
            species=result.species,
            scientific_name=result.scientific_name,
            confidence=result.confidence,
            risk=result.risk_level,
            description=result.description,
            recommendation=result.recommendation,
            image_path=image_path,
            region=region,
            latitude=latitude,
            longitude=longitude,
        )
        self.db.add(detection)
        await self.db.commit()
        await self.db.refresh(detection)
        logger.info(f"Detection created: {detection.id} - {detection.species}")
        return detection

    async def notify_region(
        self,
        detection: Detection,
        reporting_farmer_id: str,
        include_reporter: bool = False,
    ) -> int:
        query = select(Farmer).where(Farmer.region == detection.region)
        if not include_reporter:
            query = query.where(Farmer.id != reporting_farmer_id)
        result = await self.db.execute(query)
        farmers = result.scalars().all()

        if not farmers and not include_reporter:
            return 0

        notifications = []
        if include_reporter:
            existing_ids = {getattr(farmer, "id", None) for farmer in farmers}
            if reporting_farmer_id not in existing_ids:
                farmers = [SimpleNamespace(id=reporting_farmer_id), *farmers]

        for farmer in farmers:
            notification = Notification(
                farmer_id=farmer.id,
                detection_id=detection.id,
                title="⚠ Pest Alert",
                message=(
                    f"A new insect has been detected in your region.\n\n"
                    f"Species: {detection.species}\n"
                    f"Region: {detection.region}\n"
                    f"Risk: {detection.risk}\n\n"
                    f"Open AgriMent for recommendations."
                ),
                species=detection.species,
                region=detection.region,
            )
            notifications.append(notification)

        self.db.add_all(notifications)
        await self.db.commit()
        logger.info(
            f"Notified {len(notifications)} farmers in {detection.region}"
        )
        return len(notifications)

    async def get_farmer_detections(
        self, farmer_id: str, skip: int = 0, limit: int = 20
    ) -> tuple[list[Detection], int]:
        from sqlalchemy import func

        count_result = await self.db.execute(
            select(func.count(Detection.id)).where(Detection.farmer_id == farmer_id)
        )
        total = count_result.scalar() or 0

        result = await self.db.execute(
            select(Detection)
            .where(Detection.farmer_id == farmer_id)
            .order_by(Detection.created_at.desc())
            .offset(skip)
            .limit(limit)
        )
        detections = result.scalars().all()
        return list(detections), total

    def to_response(self, detection: Detection, notified_count: int = 0) -> DetectionResponse:
        return DetectionResponse(
            id=detection.id,
            species=detection.species,
            scientific_name=detection.scientific_name,
            confidence=detection.confidence,
            risk=detection.risk,
            description=detection.description,
            recommendation=detection.recommendation,
            image_url=f"/uploads/{detection.image_path}",
            region=detection.region,
            latitude=detection.latitude,
            longitude=detection.longitude,
            created_at=detection.created_at,
            notified_count=notified_count,
        )
