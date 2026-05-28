"""v43 lost hidden questions, drop private_description, path_b claim fields

Revision ID: d7a4b2c91e03
Revises: c3e8f91a2b10
Create Date: 2026-05-23

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

revision: str = "d7a4b2c91e03"
down_revision: Union[str, None] = "c3e8f91a2b10"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.drop_column("items", "private_description")

    op.add_column(
        "ihave_this_item_claims",
        sa.Column(
            "finder_answers",
            postgresql.JSONB(astext_type=sa.Text()),
            nullable=False,
            server_default="[]",
        ),
    )
    op.add_column(
        "ihave_this_item_claims",
        sa.Column(
            "attempt_scores",
            postgresql.JSONB(astext_type=sa.Text()),
            nullable=False,
            server_default="[]",
        ),
    )
    op.execute(
        """
        UPDATE ihave_this_item_claims
        SET finder_answers = jsonb_build_array(
            jsonb_build_object('legacy_description', finder_description)
        )
        WHERE finder_description IS NOT NULL AND finder_description <> ''
        """
    )
    op.drop_column("ihave_this_item_claims", "finder_description")


def downgrade() -> None:
    op.add_column(
        "ihave_this_item_claims",
        sa.Column("finder_description", sa.Text(), nullable=False, server_default=""),
    )
    op.drop_column("ihave_this_item_claims", "attempt_scores")
    op.drop_column("ihave_this_item_claims", "finder_answers")

    op.add_column("items", sa.Column("private_description", sa.Text(), nullable=True))
