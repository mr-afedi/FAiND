"""return lifecycle fields — tipping skip, dispute, tip freeze (Feature N)

Revision ID: c5f9a22b3d01
Revises: b4e8d21f6a02
Create Date: 2026-05-24

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa

revision: str = "c5f9a22b3d01"
down_revision: Union[str, None] = "b4e8d21f6a02"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.add_column(
        "item_returns",
        sa.Column("appreciation_skipped_until", sa.DateTime(timezone=True), nullable=True),
    )
    op.add_column(
        "item_returns",
        sa.Column("appreciation_sent_at", sa.DateTime(timezone=True), nullable=True),
    )
    op.add_column(
        "item_returns",
        sa.Column("tip_frozen", sa.Boolean(), nullable=False, server_default="false"),
    )
    op.add_column(
        "item_returns",
        sa.Column("dispute_filed_at", sa.DateTime(timezone=True), nullable=True),
    )
    op.add_column(
        "item_returns",
        sa.Column("dispute_filed_by_id", sa.UUID(), nullable=True),
    )
    op.add_column(
        "item_returns",
        sa.Column("dispute_reason", sa.Text(), nullable=True),
    )
    op.create_foreign_key(
        "fk_item_returns_dispute_filed_by_id_users",
        "item_returns",
        "users",
        ["dispute_filed_by_id"],
        ["id"],
        ondelete="SET NULL",
    )


def downgrade() -> None:
    op.drop_constraint(
        "fk_item_returns_dispute_filed_by_id_users",
        "item_returns",
        type_="foreignkey",
    )
    op.drop_column("item_returns", "dispute_reason")
    op.drop_column("item_returns", "dispute_filed_by_id")
    op.drop_column("item_returns", "dispute_filed_at")
    op.drop_column("item_returns", "tip_frozen")
    op.drop_column("item_returns", "appreciation_sent_at")
    op.drop_column("item_returns", "appreciation_skipped_until")
