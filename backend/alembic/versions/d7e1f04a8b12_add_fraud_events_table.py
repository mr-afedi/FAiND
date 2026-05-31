"""add fraud_events table (Feature O)

Revision ID: d7e1f04a8b12
Revises: c5f9a22b3d01
Create Date: 2026-05-22

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

revision: str = "d7e1f04a8b12"
down_revision: Union[str, None] = "c5f9a22b3d01"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None

fraud_signal_enum = postgresql.ENUM(
    "failed_verifications_2_in_24h",
    "failed_verifications_3_in_24h",
    "repeated_low_score_multi_item",
    "path_b_c_claim_failed",
    "unusual_claim_volume",
    "user_report_received",
    "admin_confirmed_fraud",
    "gradual_improvement",
    "risk_tier_high",
    name="fraudsignaltype",
    create_type=False,
)


def upgrade() -> None:
    fraud_signal_enum.create(op.get_bind(), checkfirst=True)
    op.create_table(
        "fraud_events",
        sa.Column("id", sa.UUID(), nullable=False),
        sa.Column("university_id", sa.UUID(), nullable=False),
        sa.Column("user_id", sa.UUID(), nullable=False),
        sa.Column("signal_type", fraud_signal_enum, nullable=False),
        sa.Column("delta", sa.Integer(), nullable=False),
        sa.Column("score_after", sa.Integer(), nullable=False),
        sa.Column("reference_id", sa.UUID(), nullable=True),
        sa.Column("detail", postgresql.JSONB(astext_type=sa.Text()), nullable=False),
        sa.Column("note", sa.Text(), nullable=True),
        sa.Column("applied_by_id", sa.UUID(), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.ForeignKeyConstraint(["applied_by_id"], ["users.id"], ondelete="SET NULL"),
        sa.ForeignKeyConstraint(["university_id"], ["universities.id"], ondelete="RESTRICT"),
        sa.ForeignKeyConstraint(["user_id"], ["users.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(op.f("ix_fraud_events_university_id"), "fraud_events", ["university_id"], unique=False)
    op.create_index(op.f("ix_fraud_events_user_id"), "fraud_events", ["user_id"], unique=False)
    op.create_index("ix_fraud_events_user_created", "fraud_events", ["user_id", "created_at"], unique=False)


def downgrade() -> None:
    op.drop_index("ix_fraud_events_user_created", table_name="fraud_events")
    op.drop_index(op.f("ix_fraud_events_user_id"), table_name="fraud_events")
    op.drop_index(op.f("ix_fraud_events_university_id"), table_name="fraud_events")
    op.drop_table("fraud_events")
    fraud_signal_enum.drop(op.get_bind(), checkfirst=True)
