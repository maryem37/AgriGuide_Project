from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy import select, func, delete
from sqlalchemy.ext.asyncio import AsyncSession

from database.connection import get_db
from middleware.auth import get_current_user_id
from models.notification import Notification
from schemas.notification import (
    NotificationResponse,
    NotificationListResponse,
    MarkReadRequest,
    BulkDeleteNotificationRequest,
)

router = APIRouter(prefix="/notifications", tags=["Notifications"])


@router.get("", response_model=NotificationListResponse)
async def get_notifications(
    skip: int = 0,
    limit: int = 50,
    user_id: str = Depends(get_current_user_id),
    db: AsyncSession = Depends(get_db),
):
    unread_result = await db.execute(
        select(func.count(Notification.id)).where(
            Notification.farmer_id == user_id,
            Notification.is_read == False,
        )
    )
    unread_count = unread_result.scalar() or 0

    count_result = await db.execute(
        select(func.count(Notification.id)).where(
            Notification.farmer_id == user_id,
        )
    )
    total = count_result.scalar() or 0

    result = await db.execute(
        select(Notification)
        .where(Notification.farmer_id == user_id)
        .order_by(Notification.created_at.desc())
        .offset(skip)
        .limit(limit)
    )
    notifications = result.scalars().all()

    return NotificationListResponse(
        notifications=[
            NotificationResponse(
                id=n.id,
                detection_id=n.detection_id,
                title=n.title,
                message=n.message,
                species=n.species,
                region=n.region,
                is_read=n.is_read,
                created_at=n.created_at,
            )
            for n in notifications
        ],
        unread_count=unread_count,
        total=total,
    )


@router.post("/read")
async def mark_notifications_read(
    data: MarkReadRequest,
    user_id: str = Depends(get_current_user_id),
    db: AsyncSession = Depends(get_db),
):
    from sqlalchemy import update

    query = (
        update(Notification)
        .where(
            Notification.id.in_(data.notification_ids),
            Notification.farmer_id == user_id,
        )
        .values(is_read=True)
    )

    result = await db.execute(query)
    await db.commit()

    return {"status": "updated", "count": result.rowcount}


@router.post("/bulk-delete")
async def bulk_delete_notifications(
    data: BulkDeleteNotificationRequest,
    user_id: str = Depends(get_current_user_id),
    db: AsyncSession = Depends(get_db),
):
    if not data.ids:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="No notification IDs provided",
        )

    result = await db.execute(
        select(Notification).where(
            Notification.id.in_(data.ids),
            Notification.farmer_id == user_id,
        )
    )
    notifications = result.scalars().all()

    if not notifications:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="No matching notifications found",
        )

    found_ids = [n.id for n in notifications]

    await db.execute(delete(Notification).where(Notification.id.in_(found_ids)))
    await db.commit()

    return {"deleted": len(found_ids), "ids": found_ids}
