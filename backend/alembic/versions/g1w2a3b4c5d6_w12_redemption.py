"""W12 redemption codes — Section 12.4.

Revision ID: g1w2a3b4c5d6
Revises: f0w1a2b3c4d5
Create Date: 2026-05-22

"""
from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op
from sqlalchemy import inspect
from sqlalchemy.dialects import postgresql

revision: str = "g1w2a3b4c5d6"
down_revision: Union[str, None] = "f0w1a2b3c4d5"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None

redemptioncodestatus = postgresql.ENUM(
    "active",
    "redeemed",
    "expired",
    name="redemptioncodestatus",
    create_type=False,
)


def upgrade() -> None:
    redemptioncodestatus.create(op.get_bind(), checkfirst=True)

    bind = op.get_bind()
    if "redemption_codes" in inspect(bind).get_table_names():
        op.execute(
            "ALTER TYPE adminactiontype ADD VALUE IF NOT EXISTS 'redemption_redeemed'"
        )
        return

    op.create_table(
        "redemption_codes",
        sa.Column("id", sa.UUID(), nullable=False),
        sa.Column("user_id", sa.UUID(), nullable=False),
        sa.Column("token_amount", sa.Integer(), nullable=False),
        sa.Column("code", sa.String(length=20), nullable=False),
        sa.Column("status", redemptioncodestatus, nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("expires_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("redeemed_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("redeemed_by_admin_id", sa.UUID(), nullable=True),
        sa.ForeignKeyConstraint(["redeemed_by_admin_id"], ["users.id"], ondelete="SET NULL"),
        sa.ForeignKeyConstraint(["user_id"], ["users.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("code"),
    )
    op.create_index("ix_redemption_codes_user_id", "redemption_codes", ["user_id"])
    op.create_index("ix_redemption_codes_code", "redemption_codes", ["code"])
    op.create_index("ix_redemption_codes_status", "redemption_codes", ["status"])
    op.create_index("ix_redemption_codes_expires_at", "redemption_codes", ["expires_at"])
    op.execute(
        "ALTER TYPE adminactiontype ADD VALUE IF NOT EXISTS 'redemption_redeemed'"
    )


def downgrade() -> None:
    op.drop_index("ix_redemption_codes_expires_at", table_name="redemption_codes")
    op.drop_index("ix_redemption_codes_status", table_name="redemption_codes")
    op.drop_index("ix_redemption_codes_code", table_name="redemption_codes")
    op.drop_index("ix_redemption_codes_user_id", table_name="redemption_codes")
    op.drop_table("redemption_codes")
    redemptioncodestatus.drop(op.get_bind(), checkfirst=True)
