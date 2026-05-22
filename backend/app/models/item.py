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
    POTENTIAL_MATCH     = "potential_match"
    UNDER_VERIFICATION  = "under_verification"
    UNDER_DISPUTE       = "under_dispute"
    RETURNED            = "returned"
    EXPIRED             = "expired"
    ARCHIVED            = "archived"
    CLOSED              = "closed"


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
    posted_by_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("users.id", ondelete="RESTRICT"), nullable=False, index=True
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

    # Descriptions — private_description is AES-256-GCM encrypted (Section 6)
    public_description: Mapped[str] = mapped_column(Text, nullable=False)
    private_description: Mapped[str | None] = mapped_column(Text, nullable=True)

    # Location — FK for zone + denormalized label/coords for display
    location_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True), ForeignKey("campus_zones.id", ondelete="SET NULL"), nullable=True
    )
    location_label: Mapped[str] = mapped_column(String(255), nullable=False)
    location_lat: Mapped[float | None] = mapped_column(nullable=True)
    location_lng: Mapped[float | None] = mapped_column(nullable=True)

    # Date the item was lost / found (user-provided)
    date_occurred: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)

    # Images — Cloudinary URLs, max 2 (Section 6, Section 7)
    image_urls: Mapped[list] = mapped_column(JSONB, default=list, nullable=False)

    # Lifecycle (Section 21)
    expiry_date: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    extensions_used: Mapped[int] = mapped_column(Integer, default=0, nullable=False)

    # Admin flags
    admin_locked: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)

    # Timestamps
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=lambda: datetime.now(timezone.utc), nullable=False
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        default=lambda: datetime.now(timezone.utc),
        onupdate=lambda: datetime.now(timezone.utc),
        nullable=False,
    )

    # Relationships
    posted_by: Mapped["User"] = relationship("User", foreign_keys=[posted_by_id])
    location: Mapped["CampusZone"] = relationship("CampusZone", foreign_keys=[location_id])
    hidden_questions: Mapped[list["ItemHiddenQuestion"]] = relationship(
        "ItemHiddenQuestion", back_populates="item", cascade="all, delete-orphan",
        order_by="ItemHiddenQuestion.position"
    )


class ItemHiddenQuestion(Base):
    """
    Verification Q&A for lost items (Section 6.2).
    Both question and answer are AES-256-GCM encrypted.
    Immutable after submission — no UPDATE permitted in service layer.
    """
    __tablename__ = "item_hidden_questions"

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), primary_key=True, default=uuid.uuid4
    )
    item_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("items.id", ondelete="CASCADE"), nullable=False, index=True
    )
    # question is encrypted — decrypted only during verification (never logged)
    question: Mapped[str] = mapped_column(Text, nullable=False)
    # answer is encrypted — decrypted in memory only during scoring (never returned in any API)
    answer: Mapped[str] = mapped_column(Text, nullable=False)
    position: Mapped[int] = mapped_column(Integer, nullable=False)  # 1, 2, or 3

    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=lambda: datetime.now(timezone.utc), nullable=False
    )

    item: Mapped["Item"] = relationship("Item", back_populates="hidden_questions")
