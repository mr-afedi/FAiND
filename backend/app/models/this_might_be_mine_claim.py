"""
ThisMightBeMineClaim — Path C claim records (Section 8, V4.3; scoring V4.4).

Owner claims a found item without posting a lost item first.
verification_detail stores per-attempt audit data for Feature R admin review.
"""
import uuid
from datetime import datetime, timezone

from sqlalchemy import Float, DateTime, ForeignKey, Enum
from sqlalchemy.orm import Mapped, mapped_column, relationship
from sqlalchemy.dialects.postgresql import UUID, JSONB

from app.core.database import Base
from app.models.verification_attempt import VerificationResult


class ThisMightBeMineClaim(Base):
    __tablename__ = "this_might_be_mine_claims"

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
    found_item_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("items.id", ondelete="CASCADE"),
        nullable=False, index=True,
    )
    bridge_lost_item_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("items.id", ondelete="CASCADE"),
        nullable=False,
    )
    potential_match_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("potential_matches.id", ondelete="CASCADE"),
        nullable=False, index=True,
    )
    owner_answers: Mapped[list] = mapped_column(JSONB, default=list, nullable=False)
    attempt_scores: Mapped[list] = mapped_column(JSONB, default=list, nullable=False)
    verification_detail: Mapped[dict] = mapped_column(JSONB, default=dict, nullable=False)
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
    found_item: Mapped["Item"] = relationship("Item", foreign_keys=[found_item_id])
    potential_match: Mapped["PotentialMatch"] = relationship(
        "PotentialMatch", foreign_keys=[potential_match_id]
    )
