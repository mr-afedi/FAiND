"""W3 found item reporting — tracking ref, drop point, anonymous poster.

Revision ID: z3w4d5e6f7a8
Revises: y2w3d4e5f6a7
Create Date: 2026-05-22

"""
from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op

revision: str = "z3w4d5e6f7a8"
down_revision: Union[str, None] = "y2w3d4e5f6a7"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.execute("ALTER TYPE itemstatus ADD VALUE IF NOT EXISTS 'at_droppoint'")

    op.alter_column("items", "posted_by_id", existing_type=sa.UUID(), nullable=True)

    op.add_column("items", sa.Column("drop_point_id", sa.UUID(), nullable=True))
    op.add_column("items", sa.Column("tracking_reference", sa.String(length=8), nullable=True))
    op.create_foreign_key(
        "fk_items_drop_point_id",
        "items",
        "drop_points",
        ["drop_point_id"],
        ["id"],
        ondelete="SET NULL",
    )
    op.create_index(op.f("ix_items_drop_point_id"), "items", ["drop_point_id"], unique=False)
    op.create_index(op.f("ix_items_tracking_reference"), "items", ["tracking_reference"], unique=True)


def downgrade() -> None:
    op.drop_index(op.f("ix_items_tracking_reference"), table_name="items")
    op.drop_index(op.f("ix_items_drop_point_id"), table_name="items")
    op.drop_constraint("fk_items_drop_point_id", "items", type_="foreignkey")
    op.drop_column("items", "tracking_reference")
    op.drop_column("items", "drop_point_id")
    op.alter_column("items", "posted_by_id", existing_type=sa.UUID(), nullable=False)
