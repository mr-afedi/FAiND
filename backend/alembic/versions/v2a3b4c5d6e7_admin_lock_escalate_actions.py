"""admin lock_item and escalate_dispute action types

Revision ID: v2a3b4c5d6e7
Revises: u1b2c3d4e5f6
Create Date: 2026-05-22

"""
from typing import Sequence, Union

from alembic import op

revision: str = "v2a3b4c5d6e7"
down_revision: Union[str, None] = "u1b2c3d4e5f6"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None

NEW_ADMIN_ACTIONS = ("lock_item", "escalate_dispute")


def upgrade() -> None:
    for val in NEW_ADMIN_ACTIONS:
        op.execute(f"ALTER TYPE adminactiontype ADD VALUE IF NOT EXISTS '{val}'")


def downgrade() -> None:
    pass
