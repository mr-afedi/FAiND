"""
Structured claim messaging — Section 13.2 / 13.3 (W13).
"""
import uuid
from datetime import datetime, timezone
from enum import Enum as PyEnum

from sqlalchemy import DateTime, Enum, ForeignKey, UniqueConstraint
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.core.database import Base


class InquiryMessageType(str, PyEnum):
    STILL_AVAILABLE = "still_available"
    ON_MY_WAY = "on_my_way"
    COLLECT_TOMORROW = "collect_tomorrow"


class ReplyMessageType(str, PyEnum):
    YES_HERE = "yes_here"
    COME_DURING_HOURS = "come_during_hours"
    ALREADY_COLLECTED = "already_collected"
    NO_RESPONSE_NEEDED = "no_response_needed"


INQUIRY_LABELS: dict[InquiryMessageType, str] = {
    InquiryMessageType.STILL_AVAILABLE: "Is this item still available for collection?",
    InquiryMessageType.ON_MY_WAY: "I am on my way to collect",
    InquiryMessageType.COLLECT_TOMORROW: "I cannot collect today, can I come tomorrow?",
}

REPLY_LABELS: dict[ReplyMessageType, str] = {
    ReplyMessageType.YES_HERE: "Yes, it is here",
    ReplyMessageType.COME_DURING_HOURS: "Please come between operating hours",
    ReplyMessageType.ALREADY_COLLECTED: (
        "This item has already been collected by someone else"
    ),
    ReplyMessageType.NO_RESPONSE_NEEDED: "No response needed",
}


class ClaimInquiry(Base):
    __tablename__ = "claim_inquiries"
    __table_args__ = (UniqueConstraint("claim_id", name="uq_claim_inquiry_one_per_claim"),)

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), primary_key=True, default=uuid.uuid4
    )
    claim_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("claims.id", ondelete="CASCADE"), nullable=False, index=True
    )
    message_type: Mapped[InquiryMessageType] = mapped_column(
        Enum(InquiryMessageType, name="inquirymessagetype", values_callable=lambda x: [e.value for e in x]),
        nullable=False,
    )
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        default=lambda: datetime.now(timezone.utc),
        nullable=False,
    )

    claim: Mapped["Claim"] = relationship("Claim", foreign_keys=[claim_id])
    reply: Mapped["ClaimInquiryReply | None"] = relationship(
        "ClaimInquiryReply",
        back_populates="inquiry",
        uselist=False,
        cascade="all, delete-orphan",
    )


class ClaimInquiryReply(Base):
    __tablename__ = "claim_inquiry_replies"
    __table_args__ = (UniqueConstraint("inquiry_id", name="uq_claim_inquiry_reply_one_per_inquiry"),)

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), primary_key=True, default=uuid.uuid4
    )
    inquiry_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("claim_inquiries.id", ondelete="CASCADE"), nullable=False, index=True
    )
    reply_type: Mapped[ReplyMessageType] = mapped_column(
        Enum(ReplyMessageType, name="replymessagetype", values_callable=lambda x: [e.value for e in x]),
        nullable=False,
    )
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        default=lambda: datetime.now(timezone.utc),
        nullable=False,
    )
    replied_by_authority_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("authorities.id", ondelete="SET NULL"), nullable=True
    )

    inquiry: Mapped["ClaimInquiry"] = relationship("ClaimInquiry", back_populates="reply")
