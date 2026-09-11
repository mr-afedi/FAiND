"""
PotentialMatch — AI match records (Section 10.7, Path A).

Created when match score >= 0.60. One item may have multiple matches,
ranked by score descending.
"""
import uuid
from datetime import datetime, timezone
from enum import Enum as PyEnum

from sqlalchemy import String, Float, DateTime, ForeignKey, Enum, UniqueConstraint
from sqlalchemy.orm import Mapped, mapped_column, relationship
from sqlalchemy.dialects.postgresql import UUID, JSONB

from app.core.database import Base


class PotentialMatchStatus(str, PyEnum):
    ACTIVE          = "active"          # Awaiting owner claim (Path A)
    PENDING_REVIEW  = "pending_review"  # Lower-confidence match — still claimable
    VERIFIED        = "verified"        # Legacy / return flow
    PAUSED          = "paused"          # Paused while item is UNDER_DISPUTE (Section 10.10)
    EXPIRED         = "expired"         # 14-day timeout or manual expiry (Section 21.3)


class PotentialMatch(Base):
    __tablename__ = "potential_matches"
    __table_args__ = (
        UniqueConstraint("lost_item_id", "found_item_id", name="uq_potential_match_pair"),
    )

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), primary_key=True, default=uuid.uuid4
    )
    university_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("universities.id", ondelete="RESTRICT"),
        nullable=False, index=True
    )
    lost_item_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("items.id", ondelete="CASCADE"),
        nullable=False, index=True
    )
    found_item_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("items.id", ondelete="CASCADE"),
        nullable=False, index=True
    )
    match_score: Mapped[float] = mapped_column(Float, nullable=False)
    # Per-factor scores for admin/debug visibility (Section 10.1)
    score_breakdown: Mapped[dict] = mapped_column(JSONB, default=dict, nullable=False)
    status: Mapped[PotentialMatchStatus] = mapped_column(
        Enum(PotentialMatchStatus, values_callable=lambda x: [e.value for e in x]),
        default=PotentialMatchStatus.ACTIVE,
        nullable=False,
        index=True,
    )
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        default=lambda: datetime.now(timezone.utc),
        nullable=False,
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        default=lambda: datetime.now(timezone.utc),
        onupdate=lambda: datetime.now(timezone.utc),
        nullable=False,
    )

    lost_item: Mapped["Item"] = relationship("Item", foreign_keys=[lost_item_id])
    found_item: Mapped["Item"] = relationship("Item", foreign_keys=[found_item_id])
