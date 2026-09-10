"""
Handover — condition photo + claimant details + owner sign-off (Section 11).
"""
import uuid
from datetime import datetime, timezone

from sqlalchemy import Boolean, DateTime, ForeignKey, String, Text
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.core.database import Base


class Handover(Base):
    __tablename__ = "handovers"

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), primary_key=True, default=uuid.uuid4
    )
    claim_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("claims.id", ondelete="CASCADE"), nullable=False, unique=True, index=True
    )
    item_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("items.id", ondelete="CASCADE"), nullable=False, index=True
    )
    condition_photo_url: Mapped[str] = mapped_column(String(500), nullable=False)
    claimant_name: Mapped[str] = mapped_column(String(255), nullable=False)
    claimant_phone_encrypted: Mapped[str] = mapped_column(Text, nullable=False)
    claimant_student_id_encrypted: Mapped[str | None] = mapped_column(Text, nullable=True)
    claimant_photo_url: Mapped[str | None] = mapped_column(String(500), nullable=True)
    owner_confirmed: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)
    owner_confirmed_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True), nullable=True
    )
    authority_override_note: Mapped[str | None] = mapped_column(Text, nullable=True)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        default=lambda: datetime.now(timezone.utc),
        nullable=False,
    )

    claim: Mapped["Claim"] = relationship("Claim", foreign_keys=[claim_id])
    item: Mapped["Item"] = relationship("Item", foreign_keys=[item_id])
