"""W6 authority auth — Authority model + OTP table.

Revision ID: c6w7d8e9f0a1
Revises: b5w6c7d8e9f0
Create Date: 2026-05-22

"""
from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op

revision: str = "c6w7d8e9f0a1"
down_revision: Union[str, None] = "b5w6c7d8e9f0"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table(
        "authorities",
        sa.Column("id", sa.UUID(), nullable=False),
        sa.Column("email", sa.String(length=255), nullable=False),
        sa.Column("hashed_password", sa.String(length=255), nullable=False),
        sa.Column("university_id", sa.UUID(), nullable=False),
        sa.Column("drop_point_id", sa.UUID(), nullable=False),
        sa.Column("is_active", sa.Boolean(), nullable=False, server_default=sa.true()),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
        sa.ForeignKeyConstraint(["drop_point_id"], ["drop_points.id"], ondelete="RESTRICT"),
        sa.ForeignKeyConstraint(["university_id"], ["universities.id"], ondelete="RESTRICT"),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("drop_point_id"),
    )
    op.create_index(op.f("ix_authorities_drop_point_id"), "authorities", ["drop_point_id"], unique=True)
    op.create_index(op.f("ix_authorities_email"), "authorities", ["email"], unique=True)

    op.create_table(
        "authority_otps",
        sa.Column("id", sa.UUID(), nullable=False),
        sa.Column("authority_id", sa.UUID(), nullable=False),
        sa.Column("code", sa.String(length=6), nullable=False),
        sa.Column("expires_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("is_used", sa.Boolean(), nullable=False, server_default=sa.false()),
        sa.Column("failed_attempts", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.ForeignKeyConstraint(["authority_id"], ["authorities.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(
        op.f("ix_authority_otps_authority_id"),
        "authority_otps",
        ["authority_id"],
        unique=False,
    )


def downgrade() -> None:
    op.drop_index(op.f("ix_authority_otps_authority_id"), table_name="authority_otps")
    op.drop_table("authority_otps")
    op.drop_index(op.f("ix_authorities_email"), table_name="authorities")
    op.drop_index(op.f("ix_authorities_drop_point_id"), table_name="authorities")
    op.drop_table("authorities")
