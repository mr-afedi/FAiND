"""Link handover completion to item_returns records.

Revision ID: m7w8a9b0c1d2
Revises: l6w7a8b9c0d1
Create Date: 2026-05-22

"""
from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op

revision: str = "m7w8a9b0c1d2"
down_revision: Union[str, None] = "l6w7a8b9c0d1"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.execute("ALTER TYPE returnmethod ADD VALUE IF NOT EXISTS 'handover'")
    op.alter_column("item_returns", "potential_match_id", existing_type=sa.UUID(), nullable=True)
    op.alter_column("item_returns", "found_owner_id", existing_type=sa.UUID(), nullable=True)
    op.add_column("item_returns", sa.Column("handover_id", sa.UUID(), nullable=True))
    op.create_foreign_key(
        "fk_item_returns_handover_id",
        "item_returns",
        "handovers",
        ["handover_id"],
        ["id"],
        ondelete="CASCADE",
    )
    op.create_index(op.f("ix_item_returns_handover_id"), "item_returns", ["handover_id"], unique=True)


def downgrade() -> None:
    op.drop_index(op.f("ix_item_returns_handover_id"), table_name="item_returns")
    op.drop_constraint("fk_item_returns_handover_id", "item_returns", type_="foreignkey")
    op.drop_column("item_returns", "handover_id")
    op.alter_column("item_returns", "found_owner_id", existing_type=sa.UUID(), nullable=False)
    op.alter_column("item_returns", "potential_match_id", existing_type=sa.UUID(), nullable=False)
