"""fraud signal dispute_user_flagged

Revision ID: w4c5d6e7f8a9
Revises: v3b4c5d6e7f8
Create Date: 2026-05-22

"""
from typing import Sequence, Union

from alembic import op

revision: str = "w4c5d6e7f8a9"
down_revision: Union[str, None] = "v3b4c5d6e7f8"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.execute(
        "ALTER TYPE fraudsignaltype ADD VALUE IF NOT EXISTS 'dispute_user_flagged'"
    )


def downgrade() -> None:
    pass
