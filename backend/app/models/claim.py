"""
Claim — Path A / Path C owner claims (Section 8).
"""
import uuid
from datetime import date, datetime, timezone
from enum import Enum as PyEnum

from sqlalchemy import Date, DateTime, Enum, Float, ForeignKey, String, Text, UniqueConstraint
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.core.database import Base


class ClaimPath(str, PyEnum):
    A = "A"
    C = "C"


class ClaimStatus(str, PyEnum):
    PENDING = "pending"
    VERIFIED = "verified"
    REJECTED = "rejected"


class Claim(Base):
    __tablename__ = "claims"
    __table_args__ = (
        UniqueConstraint("found_item_id", "claimant_user_id", name="uq_claim_found_claimant"),
    )

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), primary_key=True, default=uuid.uuid4
    )
    found_item_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("items.id", ondelete="CASCADE"), nullable=False, index=True
    )
    claimant_user_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("users.id", ondelete="CASCADE"), nullable=False, index=True
    )
    claim_path: Mapped[ClaimPath] = mapped_column(
        Enum(ClaimPath, name="claimpath", values_callable=lambda x: [e.value for e in x]),
        nullable=False,
    )
    photo_url: Mapped[str | None] = mapped_column(String(500), nullable=True)
    date_lost: Mapped[date | None] = mapped_column(Date, nullable=True)
    time_lost: Mapped[str | None] = mapped_column(String(5), nullable=True)
    description: Mapped[str] = mapped_column(Text, nullable=False)
    lost_location: Mapped[str | None] = mapped_column(String(255), nullable=True)
    ai_confidence_score: Mapped[float | None] = mapped_column(Float, nullable=True)
    status: Mapped[ClaimStatus] = mapped_column(
        Enum(ClaimStatus, name="claimstatus", values_callable=lambda x: [e.value for e in x]),
        default=ClaimStatus.PENDING,
        nullable=False,
        index=True,
    )
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        default=lambda: datetime.now(timezone.utc),
        nullable=False,
    )
    rejected_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True), nullable=True
    )

    found_item: Mapped["Item"] = relationship("Item", foreign_keys=[found_item_id])
    claimant: Mapped["User"] = relationship("User", foreign_keys=[claimant_user_id])
