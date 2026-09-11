"""W13 structured messaging — Section 13.2 / 13.3.

Revision ID: h2w3a4b5c6d7
Revises: g1w2a3b4c5d6
Create Date: 2026-05-22

"""
from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

revision: str = "h2w3a4b5c6d7"
down_revision: Union[str, None] = "g1w2a3b4c5d6"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None

inquirymessagetype = postgresql.ENUM(
    "still_available",
    "on_my_way",
    "collect_tomorrow",
    name="inquirymessagetype",
    create_type=False,
)
replymessagetype = postgresql.ENUM(
    "yes_here",
    "come_during_hours",
    "already_collected",
    "no_response_needed",
    name="replymessagetype",
    create_type=False,
)


def upgrade() -> None:
    inquirymessagetype.create(op.get_bind(), checkfirst=True)
    replymessagetype.create(op.get_bind(), checkfirst=True)

    op.create_table(
        "claim_inquiries",
        sa.Column("id", sa.UUID(), nullable=False),
        sa.Column("claim_id", sa.UUID(), nullable=False),
        sa.Column("message_type", inquirymessagetype, nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.ForeignKeyConstraint(["claim_id"], ["claims.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("claim_id", name="uq_claim_inquiry_one_per_claim"),
    )
    op.create_index("ix_claim_inquiries_claim_id", "claim_inquiries", ["claim_id"])

    op.create_table(
        "claim_inquiry_replies",
        sa.Column("id", sa.UUID(), nullable=False),
        sa.Column("inquiry_id", sa.UUID(), nullable=False),
        sa.Column("reply_type", replymessagetype, nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("replied_by_authority_id", sa.UUID(), nullable=True),
        sa.ForeignKeyConstraint(["inquiry_id"], ["claim_inquiries.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["replied_by_authority_id"], ["authorities.id"], ondelete="SET NULL"),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("inquiry_id", name="uq_claim_inquiry_reply_one_per_inquiry"),
    )
    op.create_index("ix_claim_inquiry_replies_inquiry_id", "claim_inquiry_replies", ["inquiry_id"])


def downgrade() -> None:
    op.drop_index("ix_claim_inquiry_replies_inquiry_id", table_name="claim_inquiry_replies")
    op.drop_table("claim_inquiry_replies")
    op.drop_index("ix_claim_inquiries_claim_id", table_name="claim_inquiries")
    op.drop_table("claim_inquiries")
    replymessagetype.drop(op.get_bind(), checkfirst=True)
    inquirymessagetype.drop(op.get_bind(), checkfirst=True)
