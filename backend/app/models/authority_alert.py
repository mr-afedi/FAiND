"""
In-app authority dashboard alerts — Section 14.1 (W16).
"""
import uuid
from datetime import datetime, timezone
from enum import Enum as PyEnum

from sqlalchemy import Boolean, DateTime, ForeignKey, String, Text, Enum
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.core.database import Base


class AuthorityAlertType(str, PyEnum):
    NEW_ITEM_INCOMING = "new_item_incoming"
    FINDER_MARKED_DROPOFF = "finder_marked_dropoff"
    NEW_CLAIM = "new_claim"
    OWNER_INQUIRY = "owner_inquiry"
    ITEM_OVERDUE = "item_overdue"
    ADMIN_ACTION = "admin_action"
    HANDOVER_COMPLETE = "handover_complete"
    ITEM_REMOVED = "item_removed"
    DROP_POINT_CLOSED = "drop_point_closed"


class AuthorityAlert(Base):
    __tablename__ = "authority_alerts"

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), primary_key=True, default=uuid.uuid4
    )
    authority_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("authorities.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    alert_type: Mapped[AuthorityAlertType] = mapped_column(
        Enum(AuthorityAlertType, values_callable=lambda x: [e.value for e in x]),
        nullable=False,
    )
    title: Mapped[str] = mapped_column(String(200), nullable=False)
    body: Mapped[str] = mapped_column(Text, nullable=False)
    link: Mapped[str | None] = mapped_column(String(500), nullable=True)
    reference_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True), nullable=True
    )
    read: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        default=lambda: datetime.now(timezone.utc),
        nullable=False,
    )

    authority: Mapped["Authority"] = relationship("Authority", foreign_keys=[authority_id])
