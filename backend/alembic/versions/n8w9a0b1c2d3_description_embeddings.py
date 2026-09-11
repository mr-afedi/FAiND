"""Add description_embedding column to items for AI matching cache.

Revision ID: n8w9a0b1c2d3
Revises: m7w8a9b0c1d2
Create Date: 2026-05-22

"""
from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

revision: str = "n8w9a0b1c2d3"
down_revision: Union[str, None] = "m7w8a9b0c1d2"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.add_column(
        "items",
        sa.Column("description_embedding", postgresql.JSONB(astext_type=sa.Text()), nullable=True),
    )


def downgrade() -> None:
    op.drop_column("items", "description_embedding")
