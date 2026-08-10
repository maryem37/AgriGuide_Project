from pydantic import BaseModel
from datetime import datetime


class NotificationResponse(BaseModel):
    id: str
    detection_id: str | None = None
    title: str
    message: str
    species: str
    region: str
    is_read: bool
    created_at: datetime

    model_config = {"from_attributes": True}


class NotificationListResponse(BaseModel):
    notifications: list[NotificationResponse]
    unread_count: int
    total: int


class MarkReadRequest(BaseModel):
    notification_ids: list[str]


class BulkDeleteNotificationRequest(BaseModel):
    ids: list[str]
