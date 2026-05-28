"""
IHaveThisItemClaim — Path B claim records (Section 8, Feature J).

Finder claims they have a lost item without posting a found item first.
"""
import uuid
from datetime import datetime, timezone
from sqlalchemy import String, Float, DateTime, ForeignKey, Text, Enum
from sqlalchemy.orm import Mapped, mapped_column, relationship
from sqlalchemy.dialects.postgresql import UUID, JSONB

from app.core.database import Base
from app.models.verification_attempt import VerificationResult


class IHaveThisItemClaim(Base):
    __tablename__ = "ihave_this_item_claims"

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
    lost_item_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("items.id", ondelete="CASCADE"),
        nullable=False, index=True,
    )
    bridge_found_item_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("items.id", ondelete="CASCADE"),
        nullable=False,
    )
    potential_match_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("potential_matches.id", ondelete="CASCADE"),
        nullable=False, index=True,
    )
    finder_answers: Mapped[list] = mapped_column(JSONB, default=list, nullable=False)
    attempt_scores: Mapped[list] = mapped_column(JSONB, default=list, nullable=False)
    location_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True), ForeignKey("campus_zones.id", ondelete="SET NULL"),
        nullable=True,
    )
    location_label: Mapped[str] = mapped_column(String(255), nullable=False)
    location_lat: Mapped[float | None] = mapped_column(nullable=True)
    location_lng: Mapped[float | None] = mapped_column(nullable=True)
    image_url: Mapped[str | None] = mapped_column(String(500), nullable=True)
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
    lost_item: Mapped["Item"] = relationship("Item", foreign_keys=[lost_item_id])
    potential_match: Mapped["PotentialMatch"] = relationship(
        "PotentialMatch", foreign_keys=[potential_match_id]
    )
