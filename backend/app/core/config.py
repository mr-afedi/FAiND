from pydantic_settings import BaseSettings
from functools import lru_cache
from typing import Optional


class Settings(BaseSettings):
    # Application
    APP_NAME: str = "FAiND"
    APP_ENV: str = "development"
    DEBUG: bool = True

    # Database
    DATABASE_URL: str

    # JWT
    SECRET_KEY: str
    ALGORITHM: str = "HS256"
    ACCESS_TOKEN_EXPIRE_MINUTES: int = 15
    REFRESH_TOKEN_EXPIRE_DAYS: int = 7

    # Encryption (AES-256-GCM) — 32-byte base64-encoded key
    ENCRYPTION_KEY: str

    # Email (SMTP)
    SMTP_HOST: str = ""
    SMTP_PORT: int = 587
    SMTP_USER: str = ""
    SMTP_PASSWORD: str = ""
    SMTP_FROM_EMAIL: str = "noreply@faind.app"
    SMTP_FROM_NAME: str = "FAiND"
    # Set to true to print emails to console instead of sending (dev mode)
    EMAIL_CONSOLE_MODE: bool = True

    # Cloudinary
    CLOUDINARY_CLOUD_NAME: str = ""
    CLOUDINARY_API_KEY: str = ""
    CLOUDINARY_API_SECRET: str = ""

    # Root Admin seeding
    ROOT_ADMIN_EMAIL: str = ""
    ROOT_ADMIN_PASSWORD: str = ""
    ROOT_ADMIN_TOTP_SECRET: str = ""

    # Admin dashboard secret path segment (Section 26.1) — e.g. "ops-7f3a"
    ADMIN_SECRET_PATH: str = ""

    # Paystack
    PAYSTACK_SECRET_KEY: str = ""
    PAYSTACK_PUBLIC_KEY: str = ""

    # Web Push (VAPID)
    VAPID_PRIVATE_KEY: str = ""
    VAPID_PUBLIC_KEY: str = ""
    VAPID_CLAIMS_EMAIL: str = ""

    # Frontend URL (for CORS + redirect links in emails)
    FRONTEND_URL: str = "http://localhost:5173"

    # Cookie settings
    COOKIE_SECURE: bool = False  # True in production (HTTPS required)
    COOKIE_SAMESITE: str = "lax"

    # Rate limiting
    RATE_LIMIT_LOGIN: str = "5/minute"
    RATE_LIMIT_REGISTER: str = "10/minute"
    RATE_LIMIT_VERIFY_EMAIL: str = "10/minute"
    RATE_LIMIT_RESEND_CODE: str = "3/minute"

    class Config:
        env_file = ".env"
        case_sensitive = True


@lru_cache()
def get_settings() -> Settings:
    return Settings()
