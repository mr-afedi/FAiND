"""
VerificationAttempt — ownership verification records (Section 12).

Path A: lost item owner answers hidden questions after AI match.
"""
import uuid
from datetime import datetime, timezone
from enum import Enum as PyEnum

from sqlalchemy import String, Float, DateTime, ForeignKey, Enum, Integer
from sqlalchemy.orm import Mapped, mapped_column, relationship
from sqlalchemy.dialects.postgresql import UUID, JSONB

from app.core.database import Base


class VerificationPath(str, PyEnum):
    PATH_A = "path_a"
    PATH_B = "path_b"
    PATH_C = "path_c"


class VerificationResult(str, PyEnum):
    APPROVED = "approved"
    REVIEW = "review"
    REJECTED = "rejected"


class VerificationAttempt(Base):
    __tablename__ = "verification_attempts"

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), primary_key=True, default=uuid.uuid4
    )
    university_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("universities.id", ondelete="RESTRICT"),
        nullable=False, index=True,
    )
    user_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("users.id", ondelete="CASCADE"),
        nullable=False, index=True,
    )
    potential_match_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("potential_matches.id", ondelete="CASCADE"),
        nullable=False, index=True,
    )
    lost_item_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("items.id", ondelete="CASCADE"),
        nullable=False, index=True,
    )
    found_item_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("items.id", ondelete="CASCADE"),
        nullable=False, index=True,
    )
    path: Mapped[VerificationPath] = mapped_column(
        Enum(VerificationPath, values_callable=lambda x: [e.value for e in x]),
        nullable=False,
    )
    ownership_score: Mapped[float] = mapped_column(Float, nullable=False)
    score_breakdown: Mapped[dict] = mapped_column(JSONB, default=dict, nullable=False)
    result: Mapped[VerificationResult] = mapped_column(
        Enum(VerificationResult, values_callable=lambda x: [e.value for e in x]),
        nullable=False,
    )
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        default=lambda: datetime.now(timezone.utc),
        nullable=False,
    )

    user: Mapped["User"] = relationship("User", foreign_keys=[user_id])
    potential_match: Mapped["PotentialMatch"] = relationship(
        "PotentialMatch", foreign_keys=[potential_match_id]
    )
