from pydantic import BaseModel, Field
from datetime import datetime


class DetectionResult(BaseModel):
    species: str
    scientific_name: str
    confidence: float = Field(..., ge=0.0, le=1.0)
    risk_level: str
    description: str
    recommendation: str


class DetectionResponse(BaseModel):
    id: str
    species: str
    scientific_name: str
    confidence: float
    risk: str
    description: str
    recommendation: str
    image_url: str
    region: str
    latitude: float | None = None
    longitude: float | None = None
    created_at: datetime
    notified_count: int = 0

    model_config = {"from_attributes": True}


class DetectionHistoryResponse(BaseModel):
    detections: list[DetectionResponse]
    total: int


class BulkDeleteRequest(BaseModel):
    ids: list[str]
