from datetime import datetime
from typing import Optional
from uuid import UUID

from pydantic import BaseModel, Field, field_validator


class RedeemTokensRequest(BaseModel):
    token_amount: int = Field(..., gt=0)

    @field_validator("token_amount")
    @classmethod
    def whole_tokens(cls, v: int) -> int:
        if v < 1:
            raise ValueError("Token amount must be at least 1.")
        return v


class RedeemTokensResponse(BaseModel):
    code: str
    token_amount: int
    expires_at: datetime
    balance_after: int


class RedemptionLookupRequest(BaseModel):
    code: str

    @field_validator("code")
    @classmethod
    def code_not_empty(cls, v: str) -> str:
        v = v.strip()
        if not v:
            raise ValueError("Redemption code is required.")
        return v


class RedemptionOwnerInfo(BaseModel):
    user_id: UUID
    username: str
    full_name: str


class RedemptionLookupResponse(BaseModel):
    code: str
    token_amount: int
    status: str
    owner: RedemptionOwnerInfo
    created_at: datetime
    expires_at: datetime
    redeemed_at: Optional[datetime] = None
    message: str
