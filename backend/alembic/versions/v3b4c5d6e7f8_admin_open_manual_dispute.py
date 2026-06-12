"""admin open_manual_dispute action type

Revision ID: v3b4c5d6e7f8
Revises: v2a3b4c5d6e7
Create Date: 2026-05-22

"""
from typing import Sequence, Union

from alembic import op

revision: str = "v3b4c5d6e7f8"
down_revision: Union[str, None] = "v2a3b4c5d6e7"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.execute(
        "ALTER TYPE adminactiontype ADD VALUE IF NOT EXISTS 'open_manual_dispute'"
    )


def downgrade() -> None:
    pass
