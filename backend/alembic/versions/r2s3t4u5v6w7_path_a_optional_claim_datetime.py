"""Make claim date_lost and time_lost optional for Path A.

Revision ID: r2s3t4u5v6w7
Revises: q1w2e3r4t5y6
Create Date: 2026-09-10

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


revision: str = "r2s3t4u5v6w7"
down_revision: Union[str, None] = "q1w2e3r4t5y6"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.alter_column(
        "claims",
        "date_lost",
        existing_type=sa.Date(),
        nullable=True,
    )
    op.alter_column(
        "claims",
        "time_lost",
        existing_type=sa.String(length=5),
        nullable=True,
    )


def downgrade() -> None:
    op.alter_column(
        "claims",
        "time_lost",
        existing_type=sa.String(length=5),
        nullable=False,
    )
    op.alter_column(
        "claims",
        "date_lost",
        existing_type=sa.Date(),
        nullable=False,
    )
