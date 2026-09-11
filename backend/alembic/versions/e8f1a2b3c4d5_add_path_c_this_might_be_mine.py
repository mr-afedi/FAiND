"""add path_c this_might_be_mine claims and path_c_bridge on items

Revision ID: e8f1a2b3c4d5
Revises: d7a4b2c91e03
Create Date: 2026-05-24

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

revision: str = "e8f1a2b3c4d5"
down_revision: Union[str, None] = "d7a4b2c91e03"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None

verification_result_enum = postgresql.ENUM(
    "approved",
    "review",
    "rejected",
    name="verificationresult",
    create_type=False,
)


def upgrade() -> None:
    op.add_column(
        "items",
        sa.Column("path_c_bridge", sa.Boolean(), nullable=False, server_default="false"),
    )
    op.create_table(
        "this_might_be_mine_claims",
        sa.Column("id", sa.UUID(), nullable=False),
        sa.Column("university_id", sa.UUID(), nullable=False),
        sa.Column("user_id", sa.UUID(), nullable=False),
        sa.Column("found_item_id", sa.UUID(), nullable=False),
        sa.Column("bridge_lost_item_id", sa.UUID(), nullable=False),
        sa.Column("potential_match_id", sa.UUID(), nullable=False),
        sa.Column("owner_answers", postgresql.JSONB(astext_type=sa.Text()), nullable=False),
        sa.Column("attempt_scores", postgresql.JSONB(astext_type=sa.Text()), nullable=False),
        sa.Column("location_id", sa.UUID(), nullable=True),
        sa.Column("location_label", sa.String(length=255), nullable=False),
        sa.Column("location_lat", sa.Float(), nullable=True),
        sa.Column("location_lng", sa.Float(), nullable=True),
        sa.Column("date_lost", sa.DateTime(timezone=True), nullable=False),
        sa.Column("ownership_score", sa.Float(), nullable=False),
        sa.Column("score_breakdown", postgresql.JSONB(astext_type=sa.Text()), nullable=False),
        sa.Column("result", verification_result_enum, nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.ForeignKeyConstraint(["bridge_lost_item_id"], ["items.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["found_item_id"], ["items.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["location_id"], ["campus_zones.id"], ondelete="SET NULL"),
        sa.ForeignKeyConstraint(["potential_match_id"], ["potential_matches.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["university_id"], ["universities.id"], ondelete="RESTRICT"),
        sa.ForeignKeyConstraint(["user_id"], ["users.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(
        op.f("ix_this_might_be_mine_claims_found_item_id"),
        "this_might_be_mine_claims",
        ["found_item_id"],
        unique=False,
    )
    op.create_index(
        op.f("ix_this_might_be_mine_claims_potential_match_id"),
        "this_might_be_mine_claims",
        ["potential_match_id"],
        unique=False,
    )
    op.create_index(
        op.f("ix_this_might_be_mine_claims_university_id"),
        "this_might_be_mine_claims",
        ["university_id"],
        unique=False,
    )
    op.create_index(
        op.f("ix_this_might_be_mine_claims_user_id"),
        "this_might_be_mine_claims",
        ["user_id"],
        unique=False,
    )


def downgrade() -> None:
    op.drop_index(op.f("ix_this_might_be_mine_claims_user_id"), table_name="this_might_be_mine_claims")
    op.drop_index(op.f("ix_this_might_be_mine_claims_university_id"), table_name="this_might_be_mine_claims")
    op.drop_index(op.f("ix_this_might_be_mine_claims_potential_match_id"), table_name="this_might_be_mine_claims")
    op.drop_index(op.f("ix_this_might_be_mine_claims_found_item_id"), table_name="this_might_be_mine_claims")
    op.drop_table("this_might_be_mine_claims")
    op.drop_column("items", "path_c_bridge")
