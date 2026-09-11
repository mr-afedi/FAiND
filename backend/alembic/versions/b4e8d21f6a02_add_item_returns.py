"""add item_returns for return confirmation

Revision ID: b4e8d21f6a02
Revises: a3b7c92d1e04
Create Date: 2026-05-22

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

revision: str = "b4e8d21f6a02"
down_revision: Union[str, None] = "a3b7c92d1e04"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None

return_method_enum = postgresql.ENUM(
    "dual_confirm",
    "qr_scan",
    name="returnmethod",
    create_type=False,
)


def upgrade() -> None:
    return_method_enum.create(op.get_bind(), checkfirst=True)
    op.create_table(
        "item_returns",
        sa.Column("id", sa.UUID(), nullable=False),
        sa.Column("university_id", sa.UUID(), nullable=False),
        sa.Column("potential_match_id", sa.UUID(), nullable=False),
        sa.Column("lost_item_id", sa.UUID(), nullable=False),
        sa.Column("found_item_id", sa.UUID(), nullable=False),
        sa.Column("lost_owner_id", sa.UUID(), nullable=False),
        sa.Column("found_owner_id", sa.UUID(), nullable=False),
        sa.Column("finder_handed_over_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("owner_received_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("returned_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("method", return_method_enum, nullable=True),
        sa.Column("qr_token_hash", sa.String(length=64), nullable=True),
        sa.Column("qr_expires_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("qr_consumed_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("tipping_window_ends_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("dispute_window_ends_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("owner_reminder_sent_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("admin_review_flagged", sa.Boolean(), nullable=False, server_default="false"),
        sa.Column("summary_note", sa.Text(), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.ForeignKeyConstraint(["found_item_id"], ["items.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["found_owner_id"], ["users.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["lost_item_id"], ["items.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["lost_owner_id"], ["users.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["potential_match_id"], ["potential_matches.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["university_id"], ["universities.id"], ondelete="RESTRICT"),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("potential_match_id"),
    )
    op.create_index(op.f("ix_item_returns_found_item_id"), "item_returns", ["found_item_id"], unique=False)
    op.create_index(op.f("ix_item_returns_lost_item_id"), "item_returns", ["lost_item_id"], unique=False)
    op.create_index(op.f("ix_item_returns_returned_at"), "item_returns", ["returned_at"], unique=False)
    op.create_index(op.f("ix_item_returns_university_id"), "item_returns", ["university_id"], unique=False)


def downgrade() -> None:
    op.drop_index(op.f("ix_item_returns_university_id"), table_name="item_returns")
    op.drop_index(op.f("ix_item_returns_returned_at"), table_name="item_returns")
    op.drop_index(op.f("ix_item_returns_lost_item_id"), table_name="item_returns")
    op.drop_index(op.f("ix_item_returns_found_item_id"), table_name="item_returns")
    op.drop_table("item_returns")
    return_method_enum.drop(op.get_bind(), checkfirst=True)
