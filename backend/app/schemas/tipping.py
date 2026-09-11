"""Tipping schemas (Section 20)."""
import uuid
from datetime import datetime
from decimal import Decimal
from typing import Optional

from pydantic import BaseModel, Field, field_validator


class InitializeTipRequest(BaseModel):
    amount_ghs: Decimal = Field(..., gt=0, description="Amount in Ghana Cedis")

    @field_validator("amount_ghs")
    @classmethod
    def validate_amount(cls, v: Decimal) -> Decimal:
        v = round(Decimal(str(v)), 2)
        if v < Decimal("1"):
            raise ValueError("Minimum appreciation amount is GHS 1.00")
        if v > Decimal("500"):
            raise ValueError("Maximum appreciation amount is GHS 500.00")
        return v


class InitializeTipResponse(BaseModel):
    tip_id: uuid.UUID
    paystack_reference: str
    authorization_url: str
    public_key: str
    amount_ghs: str


class VerifyTipResponse(BaseModel):
    status: str
    message: str
    return_id: Optional[uuid.UUID] = None


class TipHistoryItem(BaseModel):
    tip_id: uuid.UUID
    return_id: uuid.UUID
    amount_ghs: str
    currency: str
    status: str
    paid_at: Optional[datetime] = None
    created_at: datetime
    counterparty_display_name: str


class TipHistoryResponse(BaseModel):
    tips: list[TipHistoryItem]


class AdminTipDetail(BaseModel):
    tip_id: uuid.UUID
    return_id: uuid.UUID
    amount_ghs: str
    currency: str
    status: str
    paystack_reference: str
    sender_email: str
    receiver_email: str
    paid_at: Optional[datetime] = None
    created_at: datetime
