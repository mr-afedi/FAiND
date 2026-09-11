"""W8 claims — Claim model + under_claim_review item status.

Revision ID: d8w9e0f1a2b3
Revises: c6w7d8e9f0a1
Create Date: 2026-05-22

"""
from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op
from sqlalchemy import inspect
from sqlalchemy.dialects import postgresql

revision: str = "d8w9e0f1a2b3"
down_revision: Union[str, None] = "c6w7d8e9f0a1"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None

claimpath = postgresql.ENUM("A", "C", name="claimpath", create_type=False)
claimstatus = postgresql.ENUM(
    "pending", "verified", "rejected", name="claimstatus", create_type=False
)


def upgrade() -> None:
    op.execute("ALTER TYPE itemstatus ADD VALUE IF NOT EXISTS 'under_claim_review'")

    claimpath.create(op.get_bind(), checkfirst=True)
    claimstatus.create(op.get_bind(), checkfirst=True)

    bind = op.get_bind()
    if "claims" in inspect(bind).get_table_names():
        return

    op.create_table(
        "claims",
        sa.Column("id", sa.UUID(), nullable=False),
        sa.Column("found_item_id", sa.UUID(), nullable=False),
        sa.Column("claimant_user_id", sa.UUID(), nullable=False),
        sa.Column("claim_path", claimpath, nullable=False),
        sa.Column("photo_url", sa.String(length=500), nullable=True),
        sa.Column("date_lost", sa.Date(), nullable=False),
        sa.Column("time_lost", sa.String(length=5), nullable=False),
        sa.Column("description", sa.Text(), nullable=False),
        sa.Column("lost_location", sa.String(length=255), nullable=True),
        sa.Column("ai_confidence_score", sa.Float(), nullable=True),
        sa.Column("status", claimstatus, nullable=False, server_default="pending"),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.ForeignKeyConstraint(["claimant_user_id"], ["users.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["found_item_id"], ["items.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("found_item_id", "claimant_user_id", name="uq_claim_found_claimant"),
    )
    op.create_index(op.f("ix_claims_claimant_user_id"), "claims", ["claimant_user_id"], unique=False)
    op.create_index(op.f("ix_claims_found_item_id"), "claims", ["found_item_id"], unique=False)
    op.create_index(op.f("ix_claims_status"), "claims", ["status"], unique=False)
    op.alter_column("claims", "status", server_default=None)


def downgrade() -> None:
    op.drop_index(op.f("ix_claims_status"), table_name="claims")
    op.drop_index(op.f("ix_claims_found_item_id"), table_name="claims")
    op.drop_index(op.f("ix_claims_claimant_user_id"), table_name="claims")
    op.drop_table("claims")
    claimstatus.drop(op.get_bind(), checkfirst=True)
    claimpath.drop(op.get_bind(), checkfirst=True)
