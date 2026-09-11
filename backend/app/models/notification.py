"""
In-app notifications (Section 11.4 layer 1).

Web Push (Feature H) and email are layered on later; this table is the
canonical store for the bell icon and unread badge.
"""
import uuid
from datetime import datetime, timezone
from enum import Enum as PyEnum

from sqlalchemy import String, Boolean, DateTime, ForeignKey, Text, Enum
from sqlalchemy.orm import Mapped, mapped_column, relationship
from sqlalchemy.dialects.postgresql import UUID

from app.core.database import Base


class NotificationType(str, PyEnum):
    MATCH_FOUND           = "match_found"
    POTENTIAL_MATCH_EXPIRED = "potential_match_expired"
    VERIFICATION_PASSED   = "verification_passed"
    VERIFICATION_FAILED   = "verification_failed"
    VERIFICATION_REVIEW   = "verification_review"
    CLAIM_RECEIVED        = "claim_received"
    ITEM_RETURNED         = "item_returned"
    POST_EXPIRING         = "post_expiring"
    ACCOUNT_SUSPENDED     = "account_suspended"
    ACCOUNT_UNSUSPENDED   = "account_unsuspended"
    GENERAL               = "general"


class Notification(Base):
    __tablename__ = "notifications"

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), primary_key=True, default=uuid.uuid4
    )
    user_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("users.id", ondelete="CASCADE"),
        nullable=False, index=True
    )
    notification_type: Mapped[NotificationType] = mapped_column(
        Enum(NotificationType, values_callable=lambda x: [e.value for e in x]),
        nullable=False
    )
    title: Mapped[str] = mapped_column(String(200), nullable=False)
    body: Mapped[str] = mapped_column(Text, nullable=False)
    # Deep-link path, e.g. /dashboard?tab=pending
    link: Mapped[str | None] = mapped_column(String(500), nullable=True)
    reference_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True), nullable=True
    )
    read: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        default=lambda: datetime.now(timezone.utc),
        nullable=False
    )

    user: Mapped["User"] = relationship("User", foreign_keys=[user_id])
