"""W15 Admin Dashboard — new admin log action types.

Revision ID: j4w5a6b7c8d9
Revises: i3w4a5b6c7d8
Create Date: 2026-05-22

"""
from typing import Sequence, Union

from alembic import op

revision: str = "j4w5a6b7c8d9"
down_revision: Union[str, None] = "i3w4a5b6c7d8"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None

_NEW_ACTIONS = (
    "drop_point_create",
    "drop_point_update",
    "authority_create",
    "authority_activate",
    "authority_deactivate",
    "authority_reassign",
    "supervisor_create",
    "supervisor_update",
    "handover_override",
)


def upgrade() -> None:
    for val in _NEW_ACTIONS:
        op.execute(f"ALTER TYPE adminactiontype ADD VALUE IF NOT EXISTS '{val}'")


def downgrade() -> None:
    pass
