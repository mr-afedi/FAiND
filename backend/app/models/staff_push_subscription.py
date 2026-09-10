"""
StaffPushSubscription — Web Push for authority, supervisor, and admin accounts.
"""
import uuid
from datetime import datetime, timezone
from enum import Enum as PyEnum

from sqlalchemy import Boolean, DateTime, Enum, String, Text, UniqueConstraint
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column

from app.core.database import Base


class StaffPushType(str, PyEnum):
    AUTHORITY = "authority"
    SUPERVISOR = "supervisor"
    ADMIN = "admin"


class StaffPushSubscription(Base):
    __tablename__ = "staff_push_subscriptions"
    __table_args__ = (
        UniqueConstraint("staff_type", "staff_id", "endpoint", name="uq_staff_push_endpoint"),
    )

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), primary_key=True, default=uuid.uuid4
    )
    staff_type: Mapped[StaffPushType] = mapped_column(
        Enum(StaffPushType, name="staffpushtype", values_callable=lambda x: [e.value for e in x]),
        nullable=False,
    )
    staff_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), nullable=False, index=True)
    endpoint: Mapped[str] = mapped_column(Text, nullable=False)
    p256dh: Mapped[str] = mapped_column(String(512), nullable=False)
    auth: Mapped[str] = mapped_column(String(128), nullable=False)
    is_active: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        default=lambda: datetime.now(timezone.utc),
        nullable=False,
    )
