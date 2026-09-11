"""admin dashboard reinforcement — fraud override + enum values

Revision ID: s9b2c3d4e5f6
Revises: r8a1b2c3d4e5
Create Date: 2026-05-22

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa

revision: str = "s9b2c3d4e5f6"
down_revision: Union[str, None] = "r8a1b2c3d4e5"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None

NEW_FRAUD_SIGNALS = ("admin_cleared_flag", "admin_verification_override")
NEW_ADMIN_ACTIONS = (
    "clear_fraud_flag",
    "allow_verification",
    "request_more_info",
)


def upgrade() -> None:
    op.add_column(
        "users",
        sa.Column(
            "fraud_verification_override",
            sa.Boolean(),
            nullable=False,
            server_default=sa.false(),
        ),
    )
    op.alter_column("users", "fraud_verification_override", server_default=None)

    for val in NEW_FRAUD_SIGNALS:
        op.execute(f"ALTER TYPE fraudsignaltype ADD VALUE IF NOT EXISTS '{val}'")

    for val in NEW_ADMIN_ACTIONS:
        op.execute(f"ALTER TYPE adminactiontype ADD VALUE IF NOT EXISTS '{val}'")


def downgrade() -> None:
    op.drop_column("users", "fraud_verification_override")
