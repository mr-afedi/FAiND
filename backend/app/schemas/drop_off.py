from datetime import datetime
from typing import Literal, Optional

from pydantic import BaseModel, field_validator


DropOffPhase = Literal[
    "pending",
    "finder_confirmed",
    "overdue",
    "unconfirmed",
    "at_droppoint",
]


class DropOffInfo(BaseModel):
    hours_remaining: int
    hours_until_unconfirmed: int
    dropoff_phase: DropOffPhase
    finder_dropped_off_at: Optional[datetime] = None
    authority_received_at: Optional[datetime] = None
    can_confirm_drop_off: bool
    accepts_drop_off: bool
    dropoff_late: bool
    qr_payload: Optional[str] = None
    qr_image_data_url: Optional[str] = None
    qr_consumed: bool
    show_dropoff_reminder: bool

    model_config = {"from_attributes": True}


class DropOffQrRedeemRequest(BaseModel):
    token: str

    @field_validator("token")
    @classmethod
    def token_not_empty(cls, v: str) -> str:
        v = v.strip()
        if not v:
            raise ValueError("QR token is required")
        return v
