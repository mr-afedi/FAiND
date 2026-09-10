"""W4 drop-off confirmation — statuses, dual confirm, QR fields.

Revision ID: a4w5b6c7d8e9
Revises: z3w4d5e6f7a8
Create Date: 2026-05-22

"""
from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op

revision: str = "a4w5b6c7d8e9"
down_revision: Union[str, None] = "z3w4d5e6f7a8"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.execute("ALTER TYPE itemstatus ADD VALUE IF NOT EXISTS 'overdue'")
    op.execute("ALTER TYPE itemstatus ADD VALUE IF NOT EXISTS 'unconfirmed'")

    op.add_column(
        "items",
        sa.Column("finder_dropped_off_at", sa.DateTime(timezone=True), nullable=True),
    )
    op.add_column(
        "items",
        sa.Column("authority_received_at", sa.DateTime(timezone=True), nullable=True),
    )
    op.add_column(
        "items",
        sa.Column("dropoff_confirmed_at", sa.DateTime(timezone=True), nullable=True),
    )
    op.add_column("items", sa.Column("dropoff_qr_payload", sa.String(length=255), nullable=True))
    op.add_column("items", sa.Column("dropoff_qr_token_hash", sa.String(length=64), nullable=True))
    op.add_column(
        "items",
        sa.Column("dropoff_qr_consumed_at", sa.DateTime(timezone=True), nullable=True),
    )
    op.add_column(
        "items",
        sa.Column("dropoff_reminder_sent_at", sa.DateTime(timezone=True), nullable=True),
    )
    op.add_column(
        "items",
        sa.Column(
            "dropoff_late",
            sa.Boolean(),
            nullable=False,
            server_default=sa.false(),
        ),
    )
    op.alter_column("items", "dropoff_late", server_default=None)


def downgrade() -> None:
    op.drop_column("items", "dropoff_late")
    op.drop_column("items", "dropoff_reminder_sent_at")
    op.drop_column("items", "dropoff_qr_consumed_at")
    op.drop_column("items", "dropoff_qr_token_hash")
    op.drop_column("items", "dropoff_qr_payload")
    op.drop_column("items", "dropoff_confirmed_at")
    op.drop_column("items", "authority_received_at")
    op.drop_column("items", "finder_dropped_off_at")
