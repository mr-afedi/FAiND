"""W11 token settings — configurable token values (Section 12.1).

Revision ID: f0w1a2b3c4d5
Revises: e9w0f1a2b3c4
Create Date: 2026-05-22

"""
from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op

revision: str = "f0w1a2b3c4d5"
down_revision: Union[str, None] = "e9w0f1a2b3c4"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table(
        "token_settings",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("found_item_posted", sa.Integer(), nullable=False),
        sa.Column("drop_off_on_time", sa.Integer(), nullable=False),
        sa.Column("drop_off_late", sa.Integer(), nullable=False),
        sa.Column("item_claimed", sa.Integer(), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("updated_by_id", sa.UUID(), nullable=True),
        sa.ForeignKeyConstraint(["updated_by_id"], ["users.id"], ondelete="SET NULL"),
        sa.PrimaryKeyConstraint("id"),
    )
    op.execute(
        """
        INSERT INTO token_settings (
            id, found_item_posted, drop_off_on_time, drop_off_late, item_claimed, updated_at
        ) VALUES (1, 10, 40, 20, 10, NOW())
        """
    )
    op.execute(
        "ALTER TYPE adminactiontype ADD VALUE IF NOT EXISTS 'token_settings_update'"
    )


def downgrade() -> None:
    op.drop_table("token_settings")
