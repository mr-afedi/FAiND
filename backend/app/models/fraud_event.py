"""
FraudEvent — audit log for every fraud risk change (Section 18.4).

All fraud risk changes MUST go through FraudService — never update fraud_risk_score directly.
"""
import uuid
from datetime import datetime, timezone
from enum import Enum as PyEnum

from sqlalchemy import String, Integer, DateTime, ForeignKey, Enum, Text
from sqlalchemy.orm import Mapped, mapped_column, relationship
from sqlalchemy.dialects.postgresql import UUID, JSONB

from app.core.database import Base


class FraudSignalType(str, PyEnum):
    FAILED_VERIFICATIONS_2_IN_24H = "failed_verifications_2_in_24h"
    FAILED_VERIFICATIONS_3_IN_24H = "failed_verifications_3_in_24h"
    REPEATED_LOW_SCORE_MULTI_ITEM = "repeated_low_score_multi_item"
    PATH_B_C_CLAIM_FAILED = "path_b_c_claim_failed"
    UNUSUAL_CLAIM_VOLUME = "unusual_claim_volume"
    USER_REPORT_RECEIVED = "user_report_received"
    ADMIN_CONFIRMED_FRAUD = "admin_confirmed_fraud"
    ADMIN_CLEARED_FLAG = "admin_cleared_flag"
    ADMIN_VERIFICATION_OVERRIDE = "admin_verification_override"
    GRADUAL_IMPROVEMENT = "gradual_improvement"
    RISK_TIER_HIGH = "risk_tier_high"


class FraudEvent(Base):
    __tablename__ = "fraud_events"

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
    signal_type: Mapped[FraudSignalType] = mapped_column(
        Enum(FraudSignalType, values_callable=lambda x: [e.value for e in x]),
        nullable=False,
    )
    delta: Mapped[int] = mapped_column(Integer, nullable=False)
    score_after: Mapped[int] = mapped_column(Integer, nullable=False)
    reference_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True), nullable=True
    )
    detail: Mapped[dict] = mapped_column(JSONB, default=dict, nullable=False)
    note: Mapped[str | None] = mapped_column(Text, nullable=True)
    applied_by_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True), ForeignKey("users.id", ondelete="SET NULL"),
        nullable=True,
    )
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        default=lambda: datetime.now(timezone.utc),
        nullable=False,
    )

    user: Mapped["User"] = relationship("User", foreign_keys=[user_id])
    applied_by: Mapped["User | None"] = relationship(
        "User", foreign_keys=[applied_by_id]
    )
