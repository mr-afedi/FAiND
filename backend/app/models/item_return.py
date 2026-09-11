"""
ItemReturn — return confirmation state (Section 15, Feature M).

Dual confirmation and QR scan paths share one record per verified match.
"""
import uuid
from datetime import datetime, timezone
from enum import Enum as PyEnum

from sqlalchemy import String, Boolean, DateTime, ForeignKey, Enum, Text
from sqlalchemy.orm import Mapped, mapped_column, relationship
from sqlalchemy.dialects.postgresql import UUID

from app.core.database import Base


class ReturnMethod(str, PyEnum):
    DUAL_CONFIRM = "dual_confirm"
    QR_SCAN = "qr_scan"


class ItemReturn(Base):
    __tablename__ = "item_returns"

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), primary_key=True, default=uuid.uuid4
    )
    university_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("universities.id", ondelete="RESTRICT"),
        nullable=False, index=True,
    )
    potential_match_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("potential_matches.id", ondelete="CASCADE"),
        nullable=False, unique=True,
    )
    lost_item_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("items.id", ondelete="CASCADE"),
        nullable=False, index=True,
    )
    found_item_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("items.id", ondelete="CASCADE"),
        nullable=False, index=True,
    )
    lost_owner_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("users.id", ondelete="CASCADE"),
        nullable=False,
    )
    found_owner_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("users.id", ondelete="CASCADE"),
        nullable=False,
    )
    finder_handed_over_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True), nullable=True
    )
    owner_received_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True), nullable=True
    )
    returned_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True), nullable=True, index=True
    )
    method: Mapped[ReturnMethod | None] = mapped_column(
        Enum(ReturnMethod, values_callable=lambda x: [e.value for e in x]),
        nullable=True,
    )
    qr_token_hash: Mapped[str | None] = mapped_column(String(64), nullable=True)
    qr_expires_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True), nullable=True
    )
    qr_consumed_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True), nullable=True
    )
    tipping_window_ends_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True), nullable=True
    )
    dispute_window_ends_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True), nullable=True
    )
    owner_reminder_sent_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True), nullable=True
    )
    admin_review_flagged: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)
    appreciation_skipped_until: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True), nullable=True
    )
    appreciation_sent_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True), nullable=True
    )
    tip_frozen: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)
    dispute_filed_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True), nullable=True
    )
    dispute_filed_by_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True), ForeignKey("users.id", ondelete="SET NULL"), nullable=True
    )
    dispute_reason: Mapped[str | None] = mapped_column(Text, nullable=True)
    dispute_resolved_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True), nullable=True
    )
    dispute_resolution_note: Mapped[str | None] = mapped_column(Text, nullable=True)
    dispute_resolved_by_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True), ForeignKey("users.id", ondelete="SET NULL"), nullable=True
    )
    summary_note: Mapped[str | None] = mapped_column(Text, nullable=True)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        default=lambda: datetime.now(timezone.utc),
        nullable=False,
    )

    potential_match: Mapped["PotentialMatch"] = relationship(
        "PotentialMatch", foreign_keys=[potential_match_id]
    )
