"""item lifecycle scheduler fields — Feature S

Revision ID: t1a2b3c4d5e6
Revises: s9b2c3d4e5f6
Create Date: 2026-05-22

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa

revision: str = "t1a2b3c4d5e6"
down_revision: Union[str, None] = "s9b2c3d4e5f6"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.add_column(
        "items",
        sa.Column("expiry_reminder_sent_at", sa.DateTime(timezone=True), nullable=True),
    )
    op.add_column(
        "items",
        sa.Column("deletion_queued_at", sa.DateTime(timezone=True), nullable=True),
    )


def downgrade() -> None:
    op.drop_column("items", "deletion_queued_at")
    op.drop_column("items", "expiry_reminder_sent_at")
