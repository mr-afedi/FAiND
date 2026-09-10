import uuid
from datetime import datetime
from typing import Optional
from pydantic import BaseModel, field_validator


class PublicProfileResponse(BaseModel):
    id: uuid.UUID
    username: str
    full_name: str
    profile_photo_url: Optional[str] = None
    university_short_name: str
    member_since: str
    items_returned_count: int

    model_config = {"from_attributes": True}


class OwnProfileResponse(BaseModel):
    id: uuid.UUID
    email: str
    username: str
    full_name: str
    student_id: Optional[str] = None
    profile_photo_url: Optional[str] = None
    role: str
    status: str
    university_id: uuid.UUID
    university_short_name: str
    civic_alerts_enabled: bool
    push_notifications_enabled: bool
    email_notifications_enabled: bool
    member_since: str

    model_config = {"from_attributes": True}


class UpdateProfileRequest(BaseModel):
    full_name: Optional[str] = None
    student_id: Optional[str] = None
    profile_photo_url: Optional[str] = None

    @field_validator("full_name")
    @classmethod
    def validate_name(cls, v: Optional[str]) -> Optional[str]:
        if v is None:
            return v
        v = v.strip()
        if len(v) < 2:
            raise ValueError("Name must be at least 2 characters")
        if len(v) > 255:
            raise ValueError("Name must not exceed 255 characters")
        return v


class ChangePasswordRequest(BaseModel):
    current_password: str
    new_password: str
    confirm_password: str

    @field_validator("new_password")
    @classmethod
    def validate_new(cls, v: str) -> str:
        if len(v) < 8:
            raise ValueError("Password must be at least 8 characters")
        return v

    @field_validator("confirm_password")
    @classmethod
    def passwords_match(cls, v: str, info) -> str:
        if info.data.get("new_password") and v != info.data["new_password"]:
            raise ValueError("Passwords do not match")
        return v


class UpdateSettingsRequest(BaseModel):
    civic_alerts_enabled: Optional[bool] = None
    push_notifications_enabled: Optional[bool] = None
    email_notifications_enabled: Optional[bool] = None


class DeleteAccountRequest(BaseModel):
    password: str
    confirmation: str

    @field_validator("confirmation")
    @classmethod
    def must_confirm(cls, v: str) -> str:
        if v.strip().upper() != "DELETE":
            raise ValueError('Type "DELETE" to confirm account deletion')
        return v
