"""
TrustEvent — audit log for every trust score change (Section 17.5).

All changes are routed through TrustService — never written directly here.
Every row: who was affected, delta, reason, what triggered it, who applied it.
"""
import uuid
from datetime import datetime, timezone
from enum import Enum as PyEnum

from sqlalchemy import String, Integer, DateTime, ForeignKey, Enum
from sqlalchemy.orm import Mapped, mapped_column, relationship
from sqlalchemy.dialects.postgresql import UUID

from app.core.database import Base


class TrustEventReason(str, PyEnum):
    # Positive events
    FOUND_ITEM_POSTED        = "found_item_posted"         # +2  (Section 7.2)
    SUCCESSFUL_RETURN        = "successful_return"          # +5  (Section 15.3)

    # Negative events
    FAILED_VERIFICATION_2ND  = "failed_verification_2nd"   # -3  (Section 12.6)
    FAILED_VERIFICATION_3RD  = "failed_verification_3rd"   # -3  (Section 12.6)
    FALSE_CLAIM_CONFIRMED    = "false_claim_confirmed"      # -10 (Section 12.8)
    FRAUD_CONFIRMED          = "fraud_confirmed"            # -20 (Section 17.1)
    USER_REPORT_RECEIVED     = "user_report_received"       # -5  (Section 17.1)

    # Admin discretionary
    ADMIN_ADJUSTMENT         = "admin_adjustment"           # custom delta


class TrustEvent(Base):
    __tablename__ = "trust_events"

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), primary_key=True, default=uuid.uuid4
    )
    user_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("users.id", ondelete="CASCADE"),
        nullable=False, index=True
    )
    delta: Mapped[int] = mapped_column(Integer, nullable=False)
    reason: Mapped[TrustEventReason] = mapped_column(
        Enum(TrustEventReason, values_callable=lambda x: [e.value for e in x]),
        nullable=False
    )
    # Nullable UUID — points to the triggering entity (item_id, claim_id, etc.)
    reference_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True), nullable=True
    )
    # NULL = applied by system; UUID = admin who applied the change
    applied_by_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True), ForeignKey("users.id", ondelete="SET NULL"),
        nullable=True
    )
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        default=lambda: datetime.now(timezone.utc),
        nullable=False
    )

    user: Mapped["User"] = relationship("User", foreign_keys=[user_id])
    applied_by: Mapped["User | None"] = relationship("User", foreign_keys=[applied_by_id])
