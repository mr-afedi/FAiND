"""
Platform token value configuration — Section 12.1 (singleton row).
"""
from datetime import datetime, timezone

from sqlalchemy import DateTime, ForeignKey, Integer
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column

from app.core.database import Base


class TokenSettings(Base):
    __tablename__ = "token_settings"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, default=1)
    found_item_posted: Mapped[int] = mapped_column(Integer, nullable=False, default=10)
    drop_off_on_time: Mapped[int] = mapped_column(Integer, nullable=False, default=40)
    drop_off_late: Mapped[int] = mapped_column(Integer, nullable=False, default=20)
    item_claimed: Mapped[int] = mapped_column(Integer, nullable=False, default=10)
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        default=lambda: datetime.now(timezone.utc),
        onupdate=lambda: datetime.now(timezone.utc),
        nullable=False,
    )
    updated_by_id: Mapped[UUID | None] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("users.id", ondelete="SET NULL"),
        nullable=True,
    )
