import uuid
from datetime import datetime, timezone
from enum import Enum as PyEnum
from sqlalchemy import String, Boolean, DateTime, Integer, Text, ForeignKey, Enum
from sqlalchemy.orm import Mapped, mapped_column, relationship
from sqlalchemy.dialects.postgresql import UUID, JSONB
from app.core.database import Base


class ItemType(str, PyEnum):
    LOST  = "lost"
    FOUND = "found"


class ItemStatus(str, PyEnum):
    OPEN                = "open"
    FOUND               = "found"
    OVERDUE             = "overdue"
    UNCONFIRMED         = "unconfirmed"
    POTENTIAL_MATCH     = "potential_match"
    UNDER_VERIFICATION  = "under_verification"
    UNDER_DISPUTE       = "under_dispute"
    RETURNED            = "returned"
    EXPIRED             = "expired"
    ARCHIVED            = "archived"
    CLOSED              = "closed"
    AT_DROPPOINT        = "at_droppoint"
    UNDER_CLAIM_REVIEW  = "under_claim_review"


class ItemCategory(str, PyEnum):
    ELECTRONICS  = "electronics"
    BAG          = "bag"
    ID_CARD      = "id_card"
    KEYS         = "keys"
    CLOTHING     = "clothing"
    BOOKS_NOTES  = "books_notes"
    WALLET       = "wallet"
    JEWELLERY    = "jewellery"
    OTHER        = "other"


class Item(Base):
    __tablename__ = "items"

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), primary_key=True, default=uuid.uuid4
    )
    university_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("universities.id", ondelete="RESTRICT"), nullable=False, index=True
    )
    posted_by_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True), ForeignKey("users.id", ondelete="RESTRICT"), nullable=True, index=True
    )

    item_type: Mapped[ItemType] = mapped_column(
        Enum(ItemType, values_callable=lambda x: [e.value for e in x]),
        nullable=False, index=True
    )
    status: Mapped[ItemStatus] = mapped_column(
        Enum(ItemStatus, values_callable=lambda x: [e.value for e in x]),
        nullable=False, index=True
    )
    category: Mapped[ItemCategory] = mapped_column(
        Enum(ItemCategory, values_callable=lambda x: [e.value for e in x]),
        nullable=False
    )

    public_description: Mapped[str] = mapped_column(Text, nullable=False)

    description_embedding: Mapped[list | None] = mapped_column(JSONB, nullable=True)

    location_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True), ForeignKey("campus_zones.id", ondelete="SET NULL"), nullable=True
    )
    location_label: Mapped[str] = mapped_column(String(255), nullable=False)
    location_lat: Mapped[float | None] = mapped_column(nullable=True)
    location_lng: Mapped[float | None] = mapped_column(nullable=True)

    drop_point_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True), ForeignKey("drop_points.id", ondelete="SET NULL"), nullable=True, index=True
    )
    tracking_reference: Mapped[str | None] = mapped_column(
        String(8), nullable=True, unique=True, index=True
    )

    finder_dropped_off_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True), nullable=True
    )
    authority_received_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True), nullable=True
    )
    dropoff_confirmed_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True), nullable=True
    )
    dropoff_qr_payload: Mapped[str | None] = mapped_column(String(255), nullable=True)
    dropoff_qr_token_hash: Mapped[str | None] = mapped_column(String(64), nullable=True)
    dropoff_qr_consumed_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True), nullable=True
    )
    dropoff_reminder_sent_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True), nullable=True
    )
    dropoff_late: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)

    date_occurred: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)

    image_urls: Mapped[list] = mapped_column(JSONB, default=list, nullable=False)

    expiry_date: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    extensions_used: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    expiry_reminder_sent_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True), nullable=True
    )
    deletion_queued_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True), nullable=True
    )

    admin_locked: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)
    hidden_by_suspension: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)

    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=lambda: datetime.now(timezone.utc), nullable=False
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        default=lambda: datetime.now(timezone.utc),
        onupdate=lambda: datetime.now(timezone.utc),
        nullable=False,
    )

    posted_by: Mapped["User | None"] = relationship("User", foreign_keys=[posted_by_id])
    location: Mapped["CampusZone"] = relationship("CampusZone", foreign_keys=[location_id])
    drop_point: Mapped["DropPoint | None"] = relationship("DropPoint", foreign_keys=[drop_point_id])
