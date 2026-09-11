"""add path_b ihave claims and path_b_bridge on items

Revision ID: c3e8f91a2b10
Revises: a8f2c1d04e2b
Create Date: 2026-05-23

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

revision: str = "c3e8f91a2b10"
down_revision: Union[str, None] = "a8f2c1d04e2b"
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
        sa.Column("path_b_bridge", sa.Boolean(), nullable=False, server_default="false"),
    )
    op.create_table(
        "ihave_this_item_claims",
        sa.Column("id", sa.UUID(), nullable=False),
        sa.Column("university_id", sa.UUID(), nullable=False),
        sa.Column("user_id", sa.UUID(), nullable=False),
        sa.Column("lost_item_id", sa.UUID(), nullable=False),
        sa.Column("bridge_found_item_id", sa.UUID(), nullable=False),
        sa.Column("potential_match_id", sa.UUID(), nullable=False),
        sa.Column("finder_description", sa.Text(), nullable=False),
        sa.Column("location_id", sa.UUID(), nullable=True),
        sa.Column("location_label", sa.String(length=255), nullable=False),
        sa.Column("location_lat", sa.Float(), nullable=True),
        sa.Column("location_lng", sa.Float(), nullable=True),
        sa.Column("image_url", sa.String(length=500), nullable=True),
        sa.Column("ownership_score", sa.Float(), nullable=False),
        sa.Column("score_breakdown", postgresql.JSONB(astext_type=sa.Text()), nullable=False),
        sa.Column("result", verification_result_enum, nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.ForeignKeyConstraint(["bridge_found_item_id"], ["items.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["location_id"], ["campus_zones.id"], ondelete="SET NULL"),
        sa.ForeignKeyConstraint(["lost_item_id"], ["items.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["potential_match_id"], ["potential_matches.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["university_id"], ["universities.id"], ondelete="RESTRICT"),
        sa.ForeignKeyConstraint(["user_id"], ["users.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(
        op.f("ix_ihave_this_item_claims_lost_item_id"),
        "ihave_this_item_claims",
        ["lost_item_id"],
        unique=False,
    )
    op.create_index(
        op.f("ix_ihave_this_item_claims_potential_match_id"),
        "ihave_this_item_claims",
        ["potential_match_id"],
        unique=False,
    )
    op.create_index(
        op.f("ix_ihave_this_item_claims_university_id"),
        "ihave_this_item_claims",
        ["university_id"],
        unique=False,
    )
    op.create_index(
        op.f("ix_ihave_this_item_claims_user_id"),
        "ihave_this_item_claims",
        ["user_id"],
        unique=False,
    )


def downgrade() -> None:
    op.drop_index(op.f("ix_ihave_this_item_claims_user_id"), table_name="ihave_this_item_claims")
    op.drop_index(op.f("ix_ihave_this_item_claims_university_id"), table_name="ihave_this_item_claims")
    op.drop_index(op.f("ix_ihave_this_item_claims_potential_match_id"), table_name="ihave_this_item_claims")
    op.drop_index(op.f("ix_ihave_this_item_claims_lost_item_id"), table_name="ihave_this_item_claims")
    op.drop_table("ihave_this_item_claims")
    op.drop_column("items", "path_b_bridge")
