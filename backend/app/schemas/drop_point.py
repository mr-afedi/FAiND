import uuid

from pydantic import BaseModel, Field

from app.models.drop_point import DropPointType


class DropPointResponse(BaseModel):
    id: uuid.UUID
    university_id: uuid.UUID
    name: str
    type: DropPointType
    latitude: float
    longitude: float
    operating_hours: str
    is_temporarily_closed: bool
    closed_reason: str | None

    model_config = {"from_attributes": True}


class DropPointWithDistanceResponse(DropPointResponse):
    distance_km: float = Field(..., description="Geodesic distance from the query point, in kilometres")


class DropPointListResponse(BaseModel):
    drop_points: list[DropPointResponse]


class NearestDropPointResponse(BaseModel):
    nearest: DropPointWithDistanceResponse
    alternatives: list[DropPointWithDistanceResponse]
