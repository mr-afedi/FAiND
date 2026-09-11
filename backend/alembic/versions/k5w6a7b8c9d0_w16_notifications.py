"""W16 notification warnings — escrow + redemption expiry flags.

Revision ID: k5w6a7b8c9d0
Revises: j4w5a6b7c8d9
Create Date: 2026-05-22

"""
from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op

revision: str = "k5w6a7b8c9d0"
down_revision: Union[str, None] = "j4w5a6b7c8d9"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.add_column(
        "token_escrows",
        sa.Column("expiry_warning_sent_at", sa.DateTime(timezone=True), nullable=True),
    )
    op.add_column(
        "redemption_codes",
        sa.Column("expiry_warning_sent_at", sa.DateTime(timezone=True), nullable=True),
    )


def downgrade() -> None:
    op.drop_column("redemption_codes", "expiry_warning_sent_at")
    op.drop_column("token_escrows", "expiry_warning_sent_at")
