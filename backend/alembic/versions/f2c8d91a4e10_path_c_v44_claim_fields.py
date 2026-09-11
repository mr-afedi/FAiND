"""path_c v4.4: drop location/date from claims, add verification_detail

Revision ID: f2c8d91a4e10
Revises: e8f1a2b3c4d5
Create Date: 2026-05-22

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

revision: str = "f2c8d91a4e10"
down_revision: Union[str, None] = "e8f1a2b3c4d5"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.add_column(
        "this_might_be_mine_claims",
        sa.Column(
            "verification_detail",
            postgresql.JSONB(astext_type=sa.Text()),
            nullable=False,
            server_default="{}",
        ),
    )
    op.drop_constraint(
        "this_might_be_mine_claims_location_id_fkey",
        "this_might_be_mine_claims",
        type_="foreignkey",
    )
    op.drop_column("this_might_be_mine_claims", "location_id")
    op.drop_column("this_might_be_mine_claims", "location_label")
    op.drop_column("this_might_be_mine_claims", "location_lat")
    op.drop_column("this_might_be_mine_claims", "location_lng")
    op.drop_column("this_might_be_mine_claims", "date_lost")


def downgrade() -> None:
    op.add_column(
        "this_might_be_mine_claims",
        sa.Column("date_lost", sa.DateTime(timezone=True), nullable=False),
    )
    op.add_column(
        "this_might_be_mine_claims",
        sa.Column("location_lng", sa.Float(), nullable=True),
    )
    op.add_column(
        "this_might_be_mine_claims",
        sa.Column("location_lat", sa.Float(), nullable=True),
    )
    op.add_column(
        "this_might_be_mine_claims",
        sa.Column("location_label", sa.String(length=255), nullable=False),
    )
    op.add_column(
        "this_might_be_mine_claims",
        sa.Column("location_id", sa.UUID(), nullable=True),
    )
    op.create_foreign_key(
        "this_might_be_mine_claims_location_id_fkey",
        "this_might_be_mine_claims",
        "campus_zones",
        ["location_id"],
        ["id"],
        ondelete="SET NULL",
    )
    op.drop_column("this_might_be_mine_claims", "verification_detail")
