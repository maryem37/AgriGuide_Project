import uuid
from datetime import datetime, timezone
from sqlalchemy import Column, String, DateTime, Boolean, Text, ForeignKey
from sqlalchemy.orm import relationship

from database.connection import Base


class Notification(Base):
    __tablename__ = "notifications"

    id = Column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    farmer_id = Column(String(36), ForeignKey("farmers.id"), nullable=False, index=True)
    detection_id = Column(
        String(36), ForeignKey("detections.id"), nullable=True, index=True
    )
    title = Column(String(200), nullable=False)
    message = Column(Text, nullable=False)
    species = Column(String(200), nullable=False)
    region = Column(String(50), nullable=False, index=True)
    is_read = Column(Boolean, default=False, nullable=False)
    created_at = Column(
        DateTime(timezone=True), default=lambda: datetime.now(timezone.utc)
    )

    farmer = relationship("Farmer", back_populates="notifications")
