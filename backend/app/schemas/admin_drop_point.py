"""Admin drop point management schemas (W15)."""
import uuid
from datetime import datetime
from typing import Optional

from pydantic import BaseModel, Field

from app.models.drop_point import DropPointType


class AdminDropPointListItem(BaseModel):
    id: uuid.UUID
    university_id: uuid.UUID
    university_name: str
    name: str
    type: DropPointType
    latitude: float
    longitude: float
    operating_hours: str
    is_temporarily_closed: bool
    closed_reason: Optional[str] = None
    created_at: datetime
    updated_at: datetime


class AdminDropPointListResponse(BaseModel):
    drop_points: list[AdminDropPointListItem]


class CreateDropPointRequest(BaseModel):
    university_id: uuid.UUID
    name: str = Field(..., min_length=2, max_length=255)
    type: DropPointType
    latitude: float = Field(..., ge=-90, le=90)
    longitude: float = Field(..., ge=-180, le=180)
    operating_hours: str = Field(default="Mon-Fri 08:00-17:00", max_length=255)
    is_temporarily_closed: bool = False
    closed_reason: Optional[str] = Field(None, max_length=500)


class UpdateDropPointRequest(BaseModel):
    name: Optional[str] = Field(None, min_length=2, max_length=255)
    type: Optional[DropPointType] = None
    latitude: Optional[float] = Field(None, ge=-90, le=90)
    longitude: Optional[float] = Field(None, ge=-180, le=180)
    operating_hours: Optional[str] = Field(None, max_length=255)
    is_temporarily_closed: Optional[bool] = None
    closed_reason: Optional[str] = Field(None, max_length=500)
