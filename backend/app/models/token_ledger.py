"""
Token ledger — Section 12.2.

Every token credit/debit for registered users is recorded here.
"""
import uuid
from datetime import datetime, timezone
from enum import Enum as PyEnum

from sqlalchemy import DateTime, ForeignKey, Integer, Enum
from sqlalchemy.orm import Mapped, mapped_column, relationship
from sqlalchemy.dialects.postgresql import UUID

from app.core.database import Base


class TokenLedgerReason(str, PyEnum):
    FOUND_ITEM_POSTED = "found_item_posted"
    DROP_OFF_ON_TIME = "drop_off_on_time"
    DROP_OFF_LATE = "drop_off_late"
    ITEM_CLAIMED = "item_claimed"
    REDEMPTION = "redemption"
    REDEMPTION_REFUND = "redemption_refund"


class TokenLedger(Base):
    __tablename__ = "token_ledger"

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), primary_key=True, default=uuid.uuid4
    )
    user_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("users.id", ondelete="CASCADE"), nullable=False, index=True
    )
    delta: Mapped[int] = mapped_column(Integer, nullable=False)
    reason: Mapped[TokenLedgerReason] = mapped_column(
        Enum(TokenLedgerReason, values_callable=lambda x: [e.value for e in x]),
        nullable=False,
        index=True,
    )
    reference_item_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True), ForeignKey("items.id", ondelete="SET NULL"), nullable=True, index=True
    )
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        default=lambda: datetime.now(timezone.utc),
        nullable=False,
    )

    user: Mapped["User"] = relationship("User", foreign_keys=[user_id])
