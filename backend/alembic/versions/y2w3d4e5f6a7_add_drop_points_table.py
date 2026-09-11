"""add drop_points table (W2)

Revision ID: y2w3d4e5f6a7
Revises: x1w2c3d4e5f6
Create Date: 2026-05-22

"""
from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

revision: str = "y2w3d4e5f6a7"
down_revision: Union[str, None] = "x1w2c3d4e5f6"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None

droppointtype = postgresql.ENUM(
    "faculty", "security", name="droppointtype", create_type=False
)


def upgrade() -> None:
    sa.Enum("faculty", "security", name="droppointtype").create(
        op.get_bind(), checkfirst=True
    )
    op.create_table(
        "drop_points",
        sa.Column("id", sa.UUID(), nullable=False),
        sa.Column("university_id", sa.UUID(), nullable=False),
        sa.Column("name", sa.String(length=255), nullable=False),
        sa.Column("type", droppointtype, nullable=False),
        sa.Column("latitude", sa.Float(), nullable=False),
        sa.Column("longitude", sa.Float(), nullable=False),
        sa.Column(
            "operating_hours",
            sa.String(length=255),
            nullable=False,
            server_default="Mon-Fri 08:00-17:00",
        ),
        sa.Column("is_temporarily_closed", sa.Boolean(), nullable=False, server_default="false"),
        sa.Column("closed_reason", sa.Text(), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
        sa.ForeignKeyConstraint(["university_id"], ["universities.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(op.f("ix_drop_points_university_id"), "drop_points", ["university_id"])


def downgrade() -> None:
    op.drop_index(op.f("ix_drop_points_university_id"), table_name="drop_points")
    op.drop_table("drop_points")
    sa.Enum(name="droppointtype").drop(op.get_bind(), checkfirst=True)
