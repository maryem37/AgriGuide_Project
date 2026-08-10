import logging
import uuid
from pathlib import Path

from fastapi import APIRouter, Depends, File, Form, HTTPException, UploadFile, status
from sqlalchemy import select, distinct, delete
from sqlalchemy.ext.asyncio import AsyncSession

from config.settings import get_settings
from database.connection import get_db
from middleware.auth import get_current_user_id
from models.farmer import Farmer
from schemas.detection import (
    DetectionResponse,
    DetectionHistoryResponse,
    BulkDeleteRequest,
)
from services.detection_service import DetectionService
from services.vision_service import VisionService
from services.notification_service import NotificationService

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/detect", tags=["Detection"])
settings = get_settings()
ALLOWED_IMAGE_EXTENSIONS = {".jpg", ".jpeg", ".png", ".webp"}


@router.post("", response_model=DetectionResponse, status_code=status.HTTP_201_CREATED)
async def detect_insect(
    image: UploadFile = File(...),
    region: str = Form(...),
    latitude: float = Form(None),
    longitude: float = Form(None),
    farmer_id: str = Form(None),
    user_id: str = Depends(get_current_user_id),
    db: AsyncSession = Depends(get_db),
):
    actual_farmer_id = farmer_id or user_id

    if not image.content_type or not image.content_type.startswith("image/"):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="File must be an image (JPEG, PNG)",
        )

    contents = await image.read()
    if len(contents) > settings.MAX_UPLOAD_SIZE:
        raise HTTPException(
            status_code=status.HTTP_413_REQUEST_ENTITY_TOO_LARGE,
            detail=f"Image too large. Maximum size is {settings.MAX_UPLOAD_SIZE // (1024 * 1024)}MB",
        )

    upload_dir = Path(settings.UPLOAD_DIR)
    upload_dir.mkdir(parents=True, exist_ok=True)

    uploaded_name = image.filename or "upload.jpg"
    ext = Path(uploaded_name).suffix.lower()
    if ext not in ALLOWED_IMAGE_EXTENSIONS:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Unsupported image type. Use JPG, JPEG, PNG, or WebP.",
        )

    filename = f"{uuid.uuid4()}{ext}"
    filepath = upload_dir / filename
    try:
        filepath.write_bytes(contents)
    except OSError as exc:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Could not save uploaded image.",
        ) from exc

    vision_service = VisionService()
    try:
        vision_result = await vision_service.analyze_image(contents)
    except ValueError as e:
        raise HTTPException(
            status_code=status.HTTP_502_BAD_GATEWAY,
            detail=str(e),
        )

    detection_service = DetectionService(db)
    detection = await detection_service.create_detection(
        farmer_id=actual_farmer_id,
        result=vision_result,
        image_path=filename,
        region=region,
        latitude=latitude,
        longitude=longitude,
    )

    return detection_service.to_response(detection)


@router.get("/history", response_model=DetectionHistoryResponse)
async def get_history(
    skip: int = 0,
    limit: int = 20,
    farmer_id: str = None,
    user_id: str = Depends(get_current_user_id),
    db: AsyncSession = Depends(get_db),
):
    actual_farmer_id = farmer_id or user_id
    service = DetectionService(db)
    detections, total = await service.get_farmer_detections(actual_farmer_id, skip, limit)
    responses = [service.to_response(d) for d in detections]
    return DetectionHistoryResponse(detections=responses, total=total)


@router.get("/all")
async def get_all_detections(
    skip: int = 0,
    limit: int = 500,
    db: AsyncSession = Depends(get_db),
):
    from models.detection import Detection
    from models.notification import Notification
    from sqlalchemy import func

    result = await db.execute(
        select(Detection)
        .order_by(Detection.created_at.desc())
        .offset(skip)
        .limit(limit)
    )
    detections = result.scalars().all()

    notified_counts = {}
    if detections:
        detection_ids = [d.id for d in detections]
        count_result = await db.execute(
            select(
                Notification.detection_id,
                func.count(Notification.id),
            )
            .where(Notification.detection_id.in_(detection_ids))
            .group_by(Notification.detection_id)
        )
        for det_id, count in count_result.all():
            notified_counts[det_id] = count

    service = DetectionService(db)
    return {
        "detections": [
            service.to_response(d, notified_count=notified_counts.get(d.id, 0))
            for d in detections
        ],
        "total": len(detections),
    }


@router.get("/region/{region_name}")
async def get_region_detections(
    region_name: str,
    skip: int = 0,
    limit: int = 50,
    db: AsyncSession = Depends(get_db),
):
    from models.detection import Detection
    from models.notification import Notification
    from sqlalchemy import func

    result = await db.execute(
        select(Detection)
        .where(Detection.region == region_name)
        .order_by(Detection.created_at.desc())
        .offset(skip)
        .limit(limit)
    )
    detections = result.scalars().all()

    notified_counts = {}
    if detections:
        detection_ids = [d.id for d in detections]
        count_result = await db.execute(
            select(
                Notification.detection_id,
                func.count(Notification.id),
            )
            .where(Notification.detection_id.in_(detection_ids))
            .group_by(Notification.detection_id)
        )
        for det_id, count in count_result.all():
            notified_counts[det_id] = count

    service = DetectionService(db)
    return {
        "detections": [
            service.to_response(d, notified_count=notified_counts.get(d.id, 0))
            for d in detections
        ],
        "total": len(detections),
    }


@router.get("/{detection_id}", response_model=DetectionResponse)
async def get_detection(
    detection_id: str,
    user_id: str = Depends(get_current_user_id),
    db: AsyncSession = Depends(get_db),
):
    from models.detection import Detection

    result = await db.execute(select(Detection).where(Detection.id == detection_id))
    detection = result.scalar_one_or_none()
    if not detection:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Detection not found",
        )

    service = DetectionService(db)
    return service.to_response(detection)


@router.post("/{detection_id}/alert-region", response_model=DetectionResponse)
async def send_region_alert(
    detection_id: str,
    user_id: str = Depends(get_current_user_id),
    db: AsyncSession = Depends(get_db),
):
    from models.detection import Detection

    result = await db.execute(select(Detection).where(Detection.id == detection_id))
    detection = result.scalar_one_or_none()
    if not detection:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Detection not found",
        )

    if detection.farmer_id != user_id:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="You can only send alerts for your own detections",
        )

    include_sender = settings.ALERT_INCLUDE_SENDER

    detection_service = DetectionService(db)
    notified = await detection_service.notify_region(
        detection, user_id, include_reporter=include_sender
    )

    token_query = select(Farmer.device_token).where(
        Farmer.region == detection.region,
        Farmer.device_token.isnot(None),
    )
    if not include_sender:
        token_query = token_query.where(Farmer.id != user_id)
    tokens_result = await db.execute(token_query)
    tokens = [row[0] for row in tokens_result.all() if row[0]]

    logger.info(f"Found {len(tokens)} device token(s) for region '{detection.region}'")

    if tokens:
        notification_service = NotificationService()
        sent = await notification_service.send_push_notification(
            device_tokens=tokens,
            title="⚠ Pest Alert",
            body=(
                f"A new insect has been detected in your region.\n\n"
                f"Species: {detection.species}\n"
                f"Region: {detection.region}\n"
                f"Risk: {detection.risk}\n\n"
                f"Open AgriMent for recommendations."
            ),
            data={
                "detection_id": detection.id,
                "species": detection.species,
                "region": detection.region,
            },
        )
        logger.info(f"Push notification result: {sent}/{len(tokens)} sent successfully")
    else:
        logger.warning(
            f"No device tokens found for region '{detection.region}'. "
            "Push notifications require the sender to have registered a push token."
        )

    return detection_service.to_response(detection, notified_count=notified)


@router.get("/regions/list")
async def get_available_regions(
    db: AsyncSession = Depends(get_db),
):
    """
    Get list of all available regions that have detections.
    This is used for dynamic region search and autocomplete.
    Returns regions sorted alphabetically for consistent UX.
    """
    from models.detection import Detection

    result = await db.execute(
        select(distinct(Detection.region))
        .where(Detection.region.isnot(None))
        .order_by(Detection.region)
    )
    regions = [row[0] for row in result.all() if row[0]]

    return {
        "regions": regions,
        "total": len(regions),
    }


@router.get("/regions/coordinates")
async def get_region_coordinates(
    db: AsyncSession = Depends(get_db),
):
    """
    Get all regions with their geographic coordinates for map display.
    Merges database regions with known coordinate data.
    Returns a comprehensive list for map centering and autocomplete.
    """
    from models.detection import Detection
    from sqlalchemy import func

    # Fetch regions from database with their detection counts
    result = await db.execute(
        select(
            Detection.region,
            func.count(Detection.id).label("detection_count"),
            func.avg(Detection.latitude).label("avg_lat"),
            func.avg(Detection.longitude).label("avg_lng"),
        )
        .where(Detection.region.isnot(None))
        .group_by(Detection.region)
        .order_by(Detection.region)
    )
    db_regions = {
        row[0]: {
            "detection_count": row[1],
            "avg_lat": float(row[2]) if row[2] else None,
            "avg_lng": float(row[3]) if row[3] else None,
        }
        for row in result.all()
        if row[0]
    }

    # Known French region coordinates as fallback
    known_coords = {
        "Alsace": {"lat": 48.35, "lng": 7.4},
        "Auvergne-Rhone-Alpes": {"lat": 45.75, "lng": 5.05},
        "Bourgogne-Franche-Comte": {"lat": 47.0, "lng": 4.3},
        "Bretagne": {"lat": 48.2, "lng": -4.0},
        "Centre-Val de Loire": {"lat": 47.4, "lng": 1.6},
        "Corse": {"lat": 42.15, "lng": 9.1},
        "Grand Est": {"lat": 48.6, "lng": 6.2},
        "Hauts-de-France": {"lat": 49.8, "lng": 2.8},
        "Ile-de-France": {"lat": 48.85, "lng": 2.35},
        "Normandie": {"lat": 49.1, "lng": -0.4},
        "Nouvelle-Aquitaine": {"lat": 44.8, "lng": -0.5},
        "Occitanie": {"lat": 43.6, "lng": 2.0},
        "Pays de la Loire": {"lat": 47.47, "lng": -0.56},
        "Provence-Alpes-Cote d'Azur": {"lat": 43.95, "lng": 5.8},
        "Auvergne": {"lat": 45.75, "lng": 3.05},
        "Bourgogne": {"lat": 47.0, "lng": 4.3},
        "Centre": {"lat": 47.4, "lng": 1.6},
        "Champagne": {"lat": 49.0, "lng": 3.9},
        "Lorraine": {"lat": 48.9, "lng": 6.2},
        "Nord": {"lat": 50.4, "lng": 3.0},
        "Picardie": {"lat": 49.8, "lng": 2.3},
        "Provence": {"lat": 43.95, "lng": 5.8},
    }

    # Merge: use actual detection coordinates if available, else known coords
    regions = []
    all_region_names = sorted(set(list(db_regions.keys()) + list(known_coords.keys())))
    for name in all_region_names:
        info = db_regions.get(name, {})
        coords = known_coords.get(name, {"lat": 46.6, "lng": 2.2})

        lat = info.get("avg_lat") or coords["lat"]
        lng = info.get("avg_lng") or coords["lng"]

        regions.append(
            {
                "name": name,
                "latitude": lat,
                "longitude": lng,
                "detection_count": info.get("detection_count", 0),
            }
        )

    return {
        "regions": regions,
        "total": len(regions),
    }


@router.post("/bulk-delete")
async def bulk_delete_detections(
    data: BulkDeleteRequest,
    user_id: str = Depends(get_current_user_id),
    db: AsyncSession = Depends(get_db),
):
    from models.detection import Detection
    from models.notification import Notification

    if not data.ids:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="No detection IDs provided",
        )

    result = await db.execute(
        select(Detection).where(
            Detection.id.in_(data.ids),
            Detection.farmer_id == user_id,
        )
    )
    detections = result.scalars().all()

    if not detections:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="No matching detections found",
        )

    found_ids = [d.id for d in detections]

    await db.execute(
        delete(Notification).where(Notification.detection_id.in_(found_ids))
    )
    await db.execute(delete(Detection).where(Detection.id.in_(found_ids)))
    await db.commit()

    return {"deleted": len(found_ids), "ids": found_ids}
