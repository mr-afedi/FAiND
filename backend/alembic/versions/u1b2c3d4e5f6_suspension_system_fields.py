"""suspension system fields — Feature T

Revision ID: u1b2c3d4e5f6
Revises: t1a2b3c4d5e6
Create Date: 2026-05-22

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa

revision: str = "u1b2c3d4e5f6"
down_revision: Union[str, None] = "t1a2b3c4d5e6"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.add_column(
        "items",
        sa.Column(
            "hidden_by_suspension",
            sa.Boolean(),
            nullable=False,
            server_default=sa.false(),
        ),
    )
    op.add_column(
        "push_subscriptions",
        sa.Column(
            "is_active",
            sa.Boolean(),
            nullable=False,
            server_default=sa.true(),
        ),
    )
    op.add_column(
        "conversations",
        sa.Column(
            "frozen_for_suspension",
            sa.Boolean(),
            nullable=False,
            server_default=sa.false(),
        ),
    )


def downgrade() -> None:
    op.drop_column("conversations", "frozen_for_suspension")
    op.drop_column("push_subscriptions", "is_active")
    op.drop_column("items", "hidden_by_suspension")
