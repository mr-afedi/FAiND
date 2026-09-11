import uuid
from pydantic import BaseModel
from typing import Optional


class UniversityResponse(BaseModel):
    id: uuid.UUID
    name: str
    short_name: str
    email_domain: str

    model_config = {"from_attributes": True}


class CampusZoneResponse(BaseModel):
    id: uuid.UUID
    name: str
    latitude: float
    longitude: float
    university_id: uuid.UUID

    model_config = {"from_attributes": True}
