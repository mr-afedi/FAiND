"""add tip_payments table (Feature Q)

Revision ID: f1a2b3c4d5e7
Revises: e9a2b3c4d5e6
Create Date: 2026-05-22

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

revision: str = "f1a2b3c4d5e7"
down_revision: Union[str, None] = "e9a2b3c4d5e6"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None

tip_status_enum = postgresql.ENUM(
    "pending", "success", "failed", name="tippaymentstatus", create_type=False
)


def upgrade() -> None:
    tip_status_enum.create(op.get_bind(), checkfirst=True)
    op.create_table(
        "tip_payments",
        sa.Column("id", sa.UUID(), nullable=False),
        sa.Column("university_id", sa.UUID(), nullable=False),
        sa.Column("return_id", sa.UUID(), nullable=False),
        sa.Column("sender_id", sa.UUID(), nullable=False),
        sa.Column("receiver_id", sa.UUID(), nullable=False),
        sa.Column("amount_encrypted", sa.Text(), nullable=False),
        sa.Column("currency", sa.String(length=3), nullable=False),
        sa.Column("paystack_reference", sa.String(length=100), nullable=False),
        sa.Column("status", tip_status_enum, nullable=False),
        sa.Column("paid_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.ForeignKeyConstraint(["receiver_id"], ["users.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["return_id"], ["item_returns.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["sender_id"], ["users.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["university_id"], ["universities.id"], ondelete="RESTRICT"),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(op.f("ix_tip_payments_paystack_reference"), "tip_payments", ["paystack_reference"], unique=True)
    op.create_index(op.f("ix_tip_payments_return_id"), "tip_payments", ["return_id"], unique=False)
    op.create_index(op.f("ix_tip_payments_receiver_id"), "tip_payments", ["receiver_id"], unique=False)
    op.create_index(op.f("ix_tip_payments_sender_id"), "tip_payments", ["sender_id"], unique=False)


def downgrade() -> None:
    op.drop_index(op.f("ix_tip_payments_sender_id"), table_name="tip_payments")
    op.drop_index(op.f("ix_tip_payments_receiver_id"), table_name="tip_payments")
    op.drop_index(op.f("ix_tip_payments_return_id"), table_name="tip_payments")
    op.drop_index(op.f("ix_tip_payments_paystack_reference"), table_name="tip_payments")
    op.drop_table("tip_payments")
    tip_status_enum.drop(op.get_bind(), checkfirst=True)
