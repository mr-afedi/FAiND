"""W14 Drop Point Supervisor — Section 5.4 / 15.2.

Revision ID: i3w4a5b6c7d8
Revises: h2w3a4b5c6d7
Create Date: 2026-05-22

"""
from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op

revision: str = "i3w4a5b6c7d8"
down_revision: Union[str, None] = "h2w3a4b5c6d7"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table(
        "supervisors",
        sa.Column("id", sa.UUID(), nullable=False),
        sa.Column("email", sa.String(length=255), nullable=False),
        sa.Column("hashed_password", sa.String(length=255), nullable=False),
        sa.Column("university_id", sa.UUID(), nullable=False),
        sa.Column("is_active", sa.Boolean(), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
        sa.ForeignKeyConstraint(["university_id"], ["universities.id"], ondelete="RESTRICT"),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("email"),
    )
    op.create_index("ix_supervisors_email", "supervisors", ["email"], unique=True)

    op.create_table(
        "supervisor_drop_points",
        sa.Column("supervisor_id", sa.UUID(), nullable=False),
        sa.Column("drop_point_id", sa.UUID(), nullable=False),
        sa.ForeignKeyConstraint(["drop_point_id"], ["drop_points.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["supervisor_id"], ["supervisors.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("supervisor_id", "drop_point_id"),
    )


def downgrade() -> None:
    op.drop_table("supervisor_drop_points")
    op.drop_index("ix_supervisors_email", table_name="supervisors")
    op.drop_table("supervisors")
