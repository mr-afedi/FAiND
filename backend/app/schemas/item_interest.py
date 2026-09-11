import uuid
from typing import Optional

from pydantic import BaseModel


class ItemInterestStatusResponse(BaseModel):
    found_item_id: uuid.UUID
    item_status: str
    drop_point_name: Optional[str] = None
    operating_hours: Optional[str] = None
    registered: bool
    can_register: bool
    requires_interest_flow: bool
    can_claim_now: bool


class ItemInterestRegisterResponse(BaseModel):
    message: str
    drop_point_name: Optional[str] = None
    operating_hours: Optional[str] = None
