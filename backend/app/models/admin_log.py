"""AdminLog — audit trail for administrative actions (Section 4.4)."""
import uuid
from datetime import datetime, timezone
from enum import Enum as PyEnum

from sqlalchemy import String, DateTime, ForeignKey, Text, Enum
from sqlalchemy.orm import Mapped, mapped_column
from sqlalchemy.dialects.postgresql import UUID, JSONB

from app.core.database import Base


class AdminActionType(str, PyEnum):
    PROMOTE_ADMIN = "promote_admin"
    DEMOTE_ADMIN = "demote_admin"
    SUSPEND_USER = "suspend_user"
    UNSUSPEND_USER = "unsuspend_user"
    APPROVE_CLAIM = "approve_claim"
    REJECT_CLAIM = "reject_claim"
    RESOLVE_DISPUTE = "resolve_dispute"
    REMOVE_POST = "remove_post"
    FORCE_CLOSE_POST = "force_close_post"
    DISMISS_REPORT = "dismiss_report"
    WARN_USER = "warn_user"
    SUPPRESS_REPORTER = "suppress_reporter"
    CONFIRM_FRAUD = "confirm_fraud"
    CLEAR_FRAUD_FLAG = "clear_fraud_flag"
    ALLOW_VERIFICATION = "allow_verification"
    REQUEST_MORE_INFO = "request_more_info"
    TRUST_ADJUSTMENT = "trust_adjustment"


class AdminLog(Base):
    __tablename__ = "admin_logs"

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), primary_key=True, default=uuid.uuid4
    )
    admin_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("users.id", ondelete="SET NULL"),
        nullable=True, index=True,
    )
    action: Mapped[AdminActionType] = mapped_column(
        Enum(AdminActionType, values_callable=lambda x: [e.value for e in x]),
        nullable=False, index=True,
    )
    target_type: Mapped[str] = mapped_column(String(50), nullable=False)
    target_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True), nullable=True, index=True
    )
    detail: Mapped[dict] = mapped_column(JSONB, default=dict, nullable=False)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        default=lambda: datetime.now(timezone.utc),
        nullable=False,
        index=True,
    )
