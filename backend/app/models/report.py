"""
Post and user reports (Section 13).

All report mutations go through ReportService.
"""
import uuid
from datetime import datetime, timezone
from enum import Enum as PyEnum

from sqlalchemy import String, Boolean, DateTime, ForeignKey, Enum, Text, UniqueConstraint
from sqlalchemy.orm import Mapped, mapped_column, relationship
from sqlalchemy.dialects.postgresql import UUID

from app.core.database import Base


class ReportStatus(str, PyEnum):
    PENDING = "pending"
    DISMISSED = "dismissed"
    RESOLVED = "resolved"


class PostReportReason(str, PyEnum):
    FAKE_OR_MISLEADING = "fake_or_misleading"
    SUSPICIOUS_BEHAVIOR = "suspicious_behavior"
    INAPPROPRIATE_CONTENT = "inappropriate_content"
    SPAM = "spam"
    OTHER = "other"


class UserReportReason(str, PyEnum):
    THREATENING_ABUSIVE = "threatening_abusive"
    SUSPECTED_FRAUD = "suspected_fraud"
    HARASSMENT = "harassment"
    IMPERSONATION = "impersonation"
    OTHER = "other"


class AdminReportAction(str, PyEnum):
    DISMISS = "dismiss"
    REMOVE_POST = "remove_post"
    WARN_USER = "warn_user"
    SUSPEND_USER = "suspend_user"


class PostReport(Base):
    __tablename__ = "post_reports"
    __table_args__ = (
        UniqueConstraint("reporter_id", "item_id", name="uq_post_reports_reporter_item"),
    )

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), primary_key=True, default=uuid.uuid4
    )
    university_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("universities.id", ondelete="RESTRICT"),
        nullable=False, index=True,
    )
    reporter_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("users.id", ondelete="CASCADE"),
        nullable=False, index=True,
    )
    item_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("items.id", ondelete="CASCADE"),
        nullable=False, index=True,
    )
    reason: Mapped[PostReportReason] = mapped_column(
        Enum(PostReportReason, values_callable=lambda x: [e.value for e in x]),
        nullable=False,
    )
    detail_text: Mapped[str | None] = mapped_column(String(200), nullable=True)
    status: Mapped[ReportStatus] = mapped_column(
        Enum(ReportStatus, values_callable=lambda x: [e.value for e in x]),
        default=ReportStatus.PENDING,
        nullable=False,
    )
    auto_escalated: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)
    admin_action: Mapped[AdminReportAction | None] = mapped_column(
        Enum(AdminReportAction, values_callable=lambda x: [e.value for e in x]),
        nullable=True,
    )
    resolved_by_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True), ForeignKey("users.id", ondelete="SET NULL"),
        nullable=True,
    )
    resolved_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True), nullable=True
    )
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        default=lambda: datetime.now(timezone.utc),
        nullable=False,
    )

    reporter: Mapped["User"] = relationship("User", foreign_keys=[reporter_id])
    item: Mapped["Item"] = relationship("Item", foreign_keys=[item_id])
    resolved_by: Mapped["User | None"] = relationship("User", foreign_keys=[resolved_by_id])


class UserReport(Base):
    __tablename__ = "user_reports"
    __table_args__ = (
        UniqueConstraint(
            "reporter_id", "reported_user_id", name="uq_user_reports_reporter_target"
        ),
    )

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), primary_key=True, default=uuid.uuid4
    )
    university_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("universities.id", ondelete="RESTRICT"),
        nullable=False, index=True,
    )
    reporter_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("users.id", ondelete="CASCADE"),
        nullable=False, index=True,
    )
    reported_user_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("users.id", ondelete="CASCADE"),
        nullable=False, index=True,
    )
    reason: Mapped[UserReportReason] = mapped_column(
        Enum(UserReportReason, values_callable=lambda x: [e.value for e in x]),
        nullable=False,
    )
    detail_text: Mapped[str | None] = mapped_column(String(200), nullable=True)
    status: Mapped[ReportStatus] = mapped_column(
        Enum(ReportStatus, values_callable=lambda x: [e.value for e in x]),
        default=ReportStatus.PENDING,
        nullable=False,
    )
    auto_escalated: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)
    admin_action: Mapped[AdminReportAction | None] = mapped_column(
        Enum(AdminReportAction, values_callable=lambda x: [e.value for e in x]),
        nullable=True,
    )
    resolved_by_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True), ForeignKey("users.id", ondelete="SET NULL"),
        nullable=True,
    )
    resolved_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True), nullable=True
    )
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        default=lambda: datetime.now(timezone.utc),
        nullable=False,
    )

    reporter: Mapped["User"] = relationship("User", foreign_keys=[reporter_id])
    reported_user: Mapped["User"] = relationship("User", foreign_keys=[reported_user_id])
    resolved_by: Mapped["User | None"] = relationship("User", foreign_keys=[resolved_by_id])
