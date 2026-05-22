import uuid
from datetime import datetime, timezone
from enum import Enum as PyEnum
from sqlalchemy import String, Boolean, DateTime, Integer, Text, ForeignKey, Enum
from sqlalchemy.orm import Mapped, mapped_column, relationship
from sqlalchemy.dialects.postgresql import UUID
from app.core.database import Base


class UserRole(str, PyEnum):
    USER = "user"
    UNIVERSITY_ADMIN = "university_admin"
    ASSISTANT_ROOT_ADMIN = "assistant_root_admin"
    ROOT_ADMIN = "root_admin"


class AccountStatus(str, PyEnum):
    UNVERIFIED = "unverified"
    ACTIVE = "active"
    SUSPENDED = "suspended"
    DELETED = "deleted"


class User(Base):
    __tablename__ = "users"

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), primary_key=True, default=uuid.uuid4
    )
    university_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("universities.id", ondelete="RESTRICT"), nullable=False
    )
    email: Mapped[str] = mapped_column(String(255), nullable=False, unique=True, index=True)
    username: Mapped[str] = mapped_column(String(50), nullable=False, unique=True, index=True)
    full_name: Mapped[str] = mapped_column(String(255), nullable=False)
    hashed_password: Mapped[str] = mapped_column(String(255), nullable=False)

    # Optional fields
    student_id: Mapped[str | None] = mapped_column(String(50), nullable=True)
    profile_photo_url: Mapped[str | None] = mapped_column(Text, nullable=True)
    bio: Mapped[str | None] = mapped_column(Text, nullable=True)

    # Status & role
    # values_callable ensures SQLAlchemy uses enum VALUES (lowercase) not NAMES
    role: Mapped[UserRole] = mapped_column(
        Enum(UserRole, values_callable=lambda x: [e.value for e in x]),
        default=UserRole.USER, nullable=False
    )
    status: Mapped[AccountStatus] = mapped_column(
        Enum(AccountStatus, values_callable=lambda x: [e.value for e in x]),
        default=AccountStatus.UNVERIFIED, nullable=False
    )

    # Trust & fraud
    trust_score: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    fraud_risk_score: Mapped[int] = mapped_column(Integer, default=0, nullable=False)

    # Settings
    civic_alerts_enabled: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)
    push_notifications_enabled: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)
    email_notifications_enabled: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)

    # 2FA (Root Admin only)
    totp_secret: Mapped[str | None] = mapped_column(String(255), nullable=True)
    totp_enabled: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)

    # Timestamps
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=lambda: datetime.now(timezone.utc), nullable=False
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        default=lambda: datetime.now(timezone.utc),
        onupdate=lambda: datetime.now(timezone.utc),
        nullable=False,
    )
    last_login_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    suspended_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    suspended_by_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True), ForeignKey("users.id", ondelete="SET NULL"), nullable=True
    )

    # Relationships
    university: Mapped["University"] = relationship("University", back_populates="users")
    email_verifications: Mapped[list["EmailVerification"]] = relationship(
        "EmailVerification", back_populates="user", cascade="all, delete-orphan"
    )
    refresh_tokens: Mapped[list["RefreshToken"]] = relationship(
        "RefreshToken", back_populates="user", cascade="all, delete-orphan"
    )
    password_resets: Mapped[list["PasswordReset"]] = relationship(
        "PasswordReset", back_populates="user", cascade="all, delete-orphan"
    )
    push_subscriptions: Mapped[list["PushSubscription"]] = relationship(
        "PushSubscription", back_populates="user", cascade="all, delete-orphan"
    )
