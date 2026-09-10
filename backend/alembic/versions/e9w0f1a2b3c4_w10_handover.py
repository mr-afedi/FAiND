"""W10 handover — condition photo, claimant details, owner sign-off.

Revision ID: e9w0f1a2b3c4
Revises: d8w9e0f1a2b3
Create Date: 2026-05-22

"""
from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op

revision: str = "e9w0f1a2b3c4"
down_revision: Union[str, None] = "d8w9e0f1a2b3"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table(
        "handovers",
        sa.Column("id", sa.UUID(), nullable=False),
        sa.Column("claim_id", sa.UUID(), nullable=False),
        sa.Column("item_id", sa.UUID(), nullable=False),
        sa.Column("condition_photo_url", sa.String(length=500), nullable=False),
        sa.Column("claimant_name", sa.String(length=255), nullable=False),
        sa.Column("claimant_phone_encrypted", sa.Text(), nullable=False),
        sa.Column("claimant_student_id_encrypted", sa.Text(), nullable=True),
        sa.Column("claimant_photo_url", sa.String(length=500), nullable=True),
        sa.Column("owner_confirmed", sa.Boolean(), nullable=False, server_default=sa.false()),
        sa.Column("owner_confirmed_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("authority_override_note", sa.Text(), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.ForeignKeyConstraint(["claim_id"], ["claims.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["item_id"], ["items.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("claim_id"),
    )
    op.create_index(op.f("ix_handovers_claim_id"), "handovers", ["claim_id"], unique=True)
    op.create_index(op.f("ix_handovers_item_id"), "handovers", ["item_id"], unique=False)
    op.alter_column("handovers", "owner_confirmed", server_default=None)


def downgrade() -> None:
    op.drop_index(op.f("ix_handovers_item_id"), table_name="handovers")
    op.drop_index(op.f("ix_handovers_claim_id"), table_name="handovers")
    op.drop_table("handovers")
