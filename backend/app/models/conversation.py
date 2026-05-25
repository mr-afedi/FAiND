"""
Conversation — chat thread between verified parties (Section 14).

Created when Path A verification auto-approves (score > 0.75).
Feature L wires WebSocket messaging to this model.
"""
import uuid
from datetime import datetime, timezone
from enum import Enum as PyEnum

from sqlalchemy import String, DateTime, ForeignKey, Enum, UniqueConstraint
from sqlalchemy.orm import Mapped, mapped_column, relationship
from sqlalchemy.dialects.postgresql import UUID

from app.core.database import Base


class ConversationStatus(str, PyEnum):
    LOCKED = "locked"
    UNLOCKED = "unlocked"
    PAUSED = "paused"
    FROZEN = "frozen"


class Conversation(Base):
    __tablename__ = "conversations"
    __table_args__ = (
        UniqueConstraint("potential_match_id", name="uq_conversation_match"),
    )

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), primary_key=True, default=uuid.uuid4
    )
    university_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("universities.id", ondelete="RESTRICT"),
        nullable=False, index=True,
    )
    potential_match_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("potential_matches.id", ondelete="CASCADE"),
        nullable=False,
    )
    lost_item_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("items.id", ondelete="CASCADE"),
        nullable=False,
    )
    found_item_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("items.id", ondelete="CASCADE"),
        nullable=False,
    )
    lost_owner_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("users.id", ondelete="CASCADE"),
        nullable=False,
    )
    found_owner_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("users.id", ondelete="CASCADE"),
        nullable=False,
    )
    status: Mapped[ConversationStatus] = mapped_column(
        Enum(ConversationStatus, values_callable=lambda x: [e.value for e in x]),
        default=ConversationStatus.LOCKED,
        nullable=False,
    )
    unlocked_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True), nullable=True
    )
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        default=lambda: datetime.now(timezone.utc),
        nullable=False,
    )

    potential_match: Mapped["PotentialMatch"] = relationship(
        "PotentialMatch", foreign_keys=[potential_match_id]
    )
