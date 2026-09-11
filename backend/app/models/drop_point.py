import enum
import uuid
from datetime import datetime, timezone
from enum import Enum as PyEnum

from sqlalchemy import Boolean, DateTime, Enum, Float, ForeignKey, String, Text
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.core.database import Base


class DropPointType(str, PyEnum):
    FACULTY = "faculty"
    SECURITY = "security"


class DropPoint(Base):
    __tablename__ = "drop_points"

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), primary_key=True, default=uuid.uuid4
    )
    university_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("universities.id", ondelete="CASCADE"), nullable=False
    )
    name: Mapped[str] = mapped_column(String(255), nullable=False)
    type: Mapped[DropPointType] = mapped_column(
        Enum(DropPointType, name="droppointtype", values_callable=lambda x: [e.value for e in x]),
        nullable=False,
    )
    latitude: Mapped[float] = mapped_column(Float, nullable=False)
    longitude: Mapped[float] = mapped_column(Float, nullable=False)
    operating_hours: Mapped[str] = mapped_column(
        String(255), nullable=False, default="Mon-Fri 08:00-17:00"
    )
    is_temporarily_closed: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)
    closed_reason: Mapped[str | None] = mapped_column(Text, nullable=True)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=lambda: datetime.now(timezone.utc), nullable=False
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        default=lambda: datetime.now(timezone.utc),
        onupdate=lambda: datetime.now(timezone.utc),
        nullable=False,
    )

    university: Mapped["University"] = relationship("University", back_populates="drop_points")
