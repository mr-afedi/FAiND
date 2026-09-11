"""Authority in-app alerts table.

Revision ID: l6w7a8b9c0d1
Revises: k5w6a7b8c9d0
Create Date: 2026-05-22

"""
from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

revision: str = "l6w7a8b9c0d1"
down_revision: Union[str, None] = "k5w6a7b8c9d0"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None

alert_type = postgresql.ENUM(
    "new_item_incoming",
    "finder_marked_dropoff",
    "new_claim",
    "owner_inquiry",
    "item_overdue",
    "admin_action",
    "handover_complete",
    "item_removed",
    "drop_point_closed",
    name="authorityalerttype",
    create_type=False,
)


def upgrade() -> None:
    alert_type.create(op.get_bind(), checkfirst=True)
    op.create_table(
        "authority_alerts",
        sa.Column("id", sa.UUID(), nullable=False),
        sa.Column("authority_id", sa.UUID(), nullable=False),
        sa.Column("alert_type", alert_type, nullable=False),
        sa.Column("title", sa.String(length=200), nullable=False),
        sa.Column("body", sa.Text(), nullable=False),
        sa.Column("link", sa.String(length=500), nullable=True),
        sa.Column("reference_id", sa.UUID(), nullable=True),
        sa.Column("read", sa.Boolean(), nullable=False, server_default=sa.text("false")),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.ForeignKeyConstraint(["authority_id"], ["authorities.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(
        "ix_authority_alerts_authority_id",
        "authority_alerts",
        ["authority_id"],
    )


def downgrade() -> None:
    op.drop_index("ix_authority_alerts_authority_id", table_name="authority_alerts")
    op.drop_table("authority_alerts")
    op.execute(sa.text("DROP TYPE authorityalerttype"))
