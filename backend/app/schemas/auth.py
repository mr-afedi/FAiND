import uuid
from pydantic import BaseModel, EmailStr, field_validator, model_validator
from typing import Optional


class RegisterRequest(BaseModel):
    full_name: str
    username: str
    email: EmailStr
    student_id: Optional[str] = None
    password: str
    confirm_password: str
    agree_to_guidelines: bool

    @field_validator("full_name")
    @classmethod
    def validate_full_name(cls, v: str) -> str:
        v = v.strip()
        if len(v) < 2:
            raise ValueError("Full name must be at least 2 characters")
        if len(v) > 255:
            raise ValueError("Full name must not exceed 255 characters")
        return v

    @field_validator("username")
    @classmethod
    def validate_username(cls, v: str) -> str:
        v = v.strip()
        if len(v) < 3:
            raise ValueError("Username must be at least 3 characters")
        if len(v) > 50:
            raise ValueError("Username must not exceed 50 characters")
        if not v.replace("_", "").replace("-", "").replace(".", "").isalnum():
            raise ValueError("Username may only contain letters, numbers, underscores, hyphens, and dots")
        return v.lower()

    @field_validator("password")
    @classmethod
    def validate_password(cls, v: str) -> str:
        if len(v) < 8:
            raise ValueError("Password must be at least 8 characters")
        return v

    @model_validator(mode="after")
    def passwords_match(self) -> "RegisterRequest":
        if self.password != self.confirm_password:
            raise ValueError("Passwords do not match")
        if not self.agree_to_guidelines:
            raise ValueError("You must agree to the community guidelines")
        return self


class LoginRequest(BaseModel):
    email: EmailStr
    password: str


class VerifyEmailRequest(BaseModel):
    email: EmailStr
    code: str

    @field_validator("code")
    @classmethod
    def validate_code(cls, v: str) -> str:
        v = v.strip()
        if len(v) != 6 or not v.isdigit():
            raise ValueError("Code must be a 6-digit number")
        return v


class ResendVerificationRequest(BaseModel):
    email: EmailStr


class ForgotPasswordRequest(BaseModel):
    email: EmailStr


class ResetPasswordRequest(BaseModel):
    email: EmailStr
    code: str
    new_password: str
    confirm_password: str

    @field_validator("code")
    @classmethod
    def validate_code(cls, v: str) -> str:
        v = v.strip()
        if len(v) != 6 or not v.isdigit():
            raise ValueError("Code must be a 6-digit number")
        return v

    @field_validator("new_password")
    @classmethod
    def validate_new_password(cls, v: str) -> str:
        if len(v) < 8:
            raise ValueError("Password must be at least 8 characters")
        return v

    @model_validator(mode="after")
    def passwords_match(self) -> "ResetPasswordRequest":
        if self.new_password != self.confirm_password:
            raise ValueError("Passwords do not match")
        return self


class TOTPVerifyRequest(BaseModel):
    """Root Admin TOTP 2FA step — submitted after credentials pass."""
    totp_code: str
    # Temporary session token issued after credentials pass, before TOTP
    session_token: str


class TokenResponse(BaseModel):
    access_token: str
    token_type: str = "bearer"


class UserResponse(BaseModel):
    id: uuid.UUID
    email: str
    username: str
    full_name: str
    role: str
    status: str
    trust_score: int
    university_id: uuid.UUID
    profile_photo_url: Optional[str] = None

    model_config = {"from_attributes": True}


class AuthResponse(BaseModel):
    access_token: str
    token_type: str = "bearer"
    user: UserResponse


class MessageResponse(BaseModel):
    message: str


class TOTPStepResponse(BaseModel):
    """Returned to Root Admin after credentials pass — indicates TOTP step is needed."""
    requires_totp: bool = True
    session_token: str
    message: str = "Please enter your 2FA code"
