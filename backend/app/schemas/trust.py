"""Pydantic schemas for Trust System API responses (Feature E)."""
import uuid
from datetime import datetime
from typing import Optional

from pydantic import BaseModel

from app.models.trust_event import TrustEventReason


class TrustEventResponse(BaseModel):
    id: uuid.UUID
    delta: int
    reason: TrustEventReason
    reference_id: Optional[uuid.UUID] = None
    created_at: datetime

    model_config = {"from_attributes": True}


class TrustHistoryResponse(BaseModel):
    trust_score: int
    tier: str
    events: list[TrustEventResponse]
    total: int
