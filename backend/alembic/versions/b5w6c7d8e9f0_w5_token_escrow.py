"""W5 token ledger + escrow.

Revision ID: b5w6c7d8e9f0
Revises: a4w5b6c7d8e9
Create Date: 2026-05-22

"""
from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

revision: str = "b5w6c7d8e9f0"
down_revision: Union[str, None] = "a4w5b6c7d8e9"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None

token_ledger_reason = postgresql.ENUM(
    "found_item_posted",
    "drop_off_on_time",
    "drop_off_late",
    "item_claimed",
    "redemption",
    "redemption_refund",
    name="tokenledgerreason",
    create_type=False,
)


def upgrade() -> None:
    token_ledger_reason.create(op.get_bind(), checkfirst=True)

    op.create_table(
        "token_escrows",
        sa.Column("id", sa.UUID(), nullable=False),
        sa.Column("escrow_token_hash", sa.String(length=64), nullable=False),
        sa.Column("expires_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("claimed_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("claimed_by_user_id", sa.UUID(), nullable=True),
        sa.Column("discarded_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.ForeignKeyConstraint(["claimed_by_user_id"], ["users.id"], ondelete="SET NULL"),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(
        op.f("ix_token_escrows_escrow_token_hash"),
        "token_escrows",
        ["escrow_token_hash"],
        unique=True,
    )

    op.create_table(
        "token_escrow_entries",
        sa.Column("id", sa.UUID(), nullable=False),
        sa.Column("escrow_id", sa.UUID(), nullable=False),
        sa.Column("delta", sa.Integer(), nullable=False),
        sa.Column(
            "reason",
            token_ledger_reason,
            nullable=False,
        ),
        sa.Column("reference_item_id", sa.UUID(), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.ForeignKeyConstraint(["escrow_id"], ["token_escrows.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["reference_item_id"], ["items.id"], ondelete="SET NULL"),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint(
            "escrow_id",
            "reason",
            "reference_item_id",
            name="uq_token_escrow_entry_award",
        ),
    )
    op.create_index(
        op.f("ix_token_escrow_entries_escrow_id"),
        "token_escrow_entries",
        ["escrow_id"],
        unique=False,
    )
    op.create_index(
        op.f("ix_token_escrow_entries_reference_item_id"),
        "token_escrow_entries",
        ["reference_item_id"],
        unique=False,
    )

    op.create_table(
        "token_ledger",
        sa.Column("id", sa.UUID(), nullable=False),
        sa.Column("user_id", sa.UUID(), nullable=False),
        sa.Column("delta", sa.Integer(), nullable=False),
        sa.Column(
            "reason",
            token_ledger_reason,
            nullable=False,
        ),
        sa.Column("reference_item_id", sa.UUID(), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.ForeignKeyConstraint(["reference_item_id"], ["items.id"], ondelete="SET NULL"),
        sa.ForeignKeyConstraint(["user_id"], ["users.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(op.f("ix_token_ledger_user_id"), "token_ledger", ["user_id"], unique=False)
    op.create_index(op.f("ix_token_ledger_reason"), "token_ledger", ["reason"], unique=False)
    op.create_index(
        op.f("ix_token_ledger_reference_item_id"),
        "token_ledger",
        ["reference_item_id"],
        unique=False,
    )


def downgrade() -> None:
    op.drop_index(op.f("ix_token_ledger_reference_item_id"), table_name="token_ledger")
    op.drop_index(op.f("ix_token_ledger_reason"), table_name="token_ledger")
    op.drop_index(op.f("ix_token_ledger_user_id"), table_name="token_ledger")
    op.drop_table("token_ledger")
    op.drop_index(op.f("ix_token_escrow_entries_reference_item_id"), table_name="token_escrow_entries")
    op.drop_index(op.f("ix_token_escrow_entries_escrow_id"), table_name="token_escrow_entries")
    op.drop_table("token_escrow_entries")
    op.drop_index(op.f("ix_token_escrows_escrow_token_hash"), table_name="token_escrows")
    op.drop_table("token_escrows")
    token_ledger_reason.drop(op.get_bind(), checkfirst=True)
