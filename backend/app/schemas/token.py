from datetime import datetime
from typing import Optional
from uuid import UUID

from pydantic import BaseModel, ConfigDict, EmailStr, Field, field_validator

from app.schemas.auth import RegisterRequest


class TokenEscrowInfo(BaseModel):
    show_registration_prompt: bool
    pending_total: int
    escrow_token: Optional[str] = None
    expiring_soon: bool = False


class EscrowDiscardRequest(BaseModel):
    escrow_token: str

    @field_validator("escrow_token")
    @classmethod
    def token_not_empty(cls, v: str) -> str:
        v = v.strip()
        if not v:
            raise ValueError("Escrow token is required")
        return v


class EscrowClaimLoginRequest(BaseModel):
    escrow_token: str
    email: EmailStr
    password: str

    @field_validator("escrow_token")
    @classmethod
    def token_not_empty(cls, v: str) -> str:
        v = v.strip()
        if not v:
            raise ValueError("Escrow token is required")
        return v


class EscrowClaimRegisterRequest(RegisterRequest):
    escrow_token: str

    @field_validator("escrow_token")
    @classmethod
    def token_not_empty(cls, v: str) -> str:
        v = v.strip()
        if not v:
            raise ValueError("Escrow token is required")
        return v


class EscrowClaimMeRequest(BaseModel):
    escrow_token: str

    @field_validator("escrow_token")
    @classmethod
    def token_not_empty(cls, v: str) -> str:
        v = v.strip()
        if not v:
            raise ValueError("Escrow token is required")
        return v


class EscrowClaimResponse(BaseModel):
    message: str
    tokens_claimed: int
    pending_total: int = 0


class EscrowClaimLoginResponse(EscrowClaimResponse):
    access_token: str
    token_type: str = "bearer"


class EscrowStatusResponse(BaseModel):
    escrow: TokenEscrowInfo


class TokenLedgerEntryResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: UUID
    delta: int
    reason: str
    reference_item_id: Optional[UUID] = None
    created_at: datetime


class UserTokensResponse(BaseModel):
    balance: int
    recent: list[TokenLedgerEntryResponse]


class TokenSettingsResponse(BaseModel):
    found_item_posted: int
    drop_off_on_time: int
    drop_off_late: int
    item_claimed: int
    updated_at: datetime


class TokenSettingsUpdate(BaseModel):
    found_item_posted: Optional[int] = Field(default=None, ge=0)
    drop_off_on_time: Optional[int] = Field(default=None, ge=0)
    drop_off_late: Optional[int] = Field(default=None, ge=0)
    item_claimed: Optional[int] = Field(default=None, ge=0)
