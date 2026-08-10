import uuid
from datetime import datetime, timezone
from sqlalchemy import Column, String, DateTime, Float, Text, ForeignKey
from sqlalchemy.orm import relationship

from database.connection import Base


class Detection(Base):
    __tablename__ = "detections"

    id = Column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    farmer_id = Column(String(36), ForeignKey("farmers.id"), nullable=False, index=True)
    species = Column(String(200), nullable=False)
    scientific_name = Column(String(200), nullable=False)
    confidence = Column(Float, nullable=False)
    risk = Column(String(50), nullable=False)
    description = Column(Text, nullable=False)
    recommendation = Column(Text, nullable=False)
    image_path = Column(String(500), nullable=False)
    region = Column(String(50), nullable=False, index=True)
    latitude = Column(Float, nullable=True)
    longitude = Column(Float, nullable=True)
    created_at = Column(DateTime(timezone=True), default=lambda: datetime.now(timezone.utc))

    farmer = relationship("Farmer", back_populates="detections")
