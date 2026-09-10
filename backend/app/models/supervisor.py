"""
Drop Point Supervisor — Section 5.4 / 15.2 (W14).
"""
import uuid
from datetime import datetime, timezone

from sqlalchemy import Boolean, DateTime, ForeignKey, String, Table, Column
from sqlalchemy.orm import Mapped, mapped_column, relationship
from sqlalchemy.dialects.postgresql import UUID

from app.core.database import Base

supervisor_drop_points = Table(
    "supervisor_drop_points",
    Base.metadata,
    Column(
        "supervisor_id",
        UUID(as_uuid=True),
        ForeignKey("supervisors.id", ondelete="CASCADE"),
        primary_key=True,
    ),
    Column(
        "drop_point_id",
        UUID(as_uuid=True),
        ForeignKey("drop_points.id", ondelete="CASCADE"),
        primary_key=True,
    ),
)


class Supervisor(Base):
    __tablename__ = "supervisors"

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), primary_key=True, default=uuid.uuid4
    )
    email: Mapped[str] = mapped_column(String(255), nullable=False, unique=True, index=True)
    hashed_password: Mapped[str] = mapped_column(String(255), nullable=False)
    university_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("universities.id", ondelete="RESTRICT"), nullable=False
    )
    is_active: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)
    push_notifications_enabled: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=lambda: datetime.now(timezone.utc), nullable=False
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        default=lambda: datetime.now(timezone.utc),
        onupdate=lambda: datetime.now(timezone.utc),
        nullable=False,
    )

    university: Mapped["University"] = relationship("University", foreign_keys=[university_id])
    drop_points: Mapped[list["DropPoint"]] = relationship(
        "DropPoint",
        secondary=supervisor_drop_points,
    )
