"""W1 V5 removal pass — drop chat, trust, tipping, fraud, verification tables

Revision ID: x1w2c3d4e5f6
Revises: w4c5d6e7f8a9
Create Date: 2026-06-19

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa

revision: str = "x1w2c3d4e5f6"
down_revision: Union[str, None] = "w4c5d6e7f8a9"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # Demote assistant admins before enum change
    op.execute(
        "UPDATE users SET role = 'user' WHERE role = 'assistant_root_admin'"
    )

    # Drop FK from user_reports before conversations
    op.drop_column("user_reports", "context_conversation_id")

    # Drop removed feature tables (order: dependents first)
    op.drop_table("messages")
    op.drop_table("conversations")
    op.drop_table("trust_events")
    op.drop_table("tip_payments")
    op.drop_table("ihave_this_item_claims")
    op.drop_table("this_might_be_mine_claims")
    op.drop_table("verification_attempts")
    op.drop_table("fraud_events")
    op.drop_table("item_hidden_questions")

    # User trust/fraud columns
    op.drop_column("users", "trust_score")
    op.drop_column("users", "fraud_risk_score")
    op.drop_column("users", "fraud_verification_override")

    # Item path bridge columns
    op.drop_column("items", "path_b_bridge")
    op.drop_column("items", "path_c_bridge")

    # Return tipping columns
    op.drop_column("item_returns", "tipping_window_ends_at")
    op.drop_column("item_returns", "appreciation_skipped_until")
    op.drop_column("item_returns", "appreciation_sent_at")
    op.drop_column("item_returns", "tip_frozen")

    # Remove assistant_root_admin from userrole enum
    op.execute("ALTER TYPE userrole RENAME TO userrole_old")
    op.execute(
        "CREATE TYPE userrole AS ENUM ('user', 'university_admin', 'root_admin')"
    )
    op.execute(
        "ALTER TABLE users ALTER COLUMN role TYPE userrole "
        "USING role::text::userrole"
    )
    op.execute("DROP TYPE userrole_old")


def downgrade() -> None:
    # Recreate userrole with assistant_root_admin
    op.execute("ALTER TYPE userrole RENAME TO userrole_old")
    op.execute(
        "CREATE TYPE userrole AS ENUM ("
        "'user', 'university_admin', 'assistant_root_admin', 'root_admin'"
        ")"
    )
    op.execute(
        "ALTER TABLE users ALTER COLUMN role TYPE userrole "
        "USING role::text::userrole"
    )
    op.execute("DROP TYPE userrole_old")

    op.add_column(
        "item_returns",
        sa.Column("tip_frozen", sa.Boolean(), nullable=False, server_default="false"),
    )
    op.add_column(
        "item_returns",
        sa.Column("appreciation_sent_at", sa.DateTime(timezone=True), nullable=True),
    )
    op.add_column(
        "item_returns",
        sa.Column("appreciation_skipped_until", sa.DateTime(timezone=True), nullable=True),
    )
    op.add_column(
        "item_returns",
        sa.Column("tipping_window_ends_at", sa.DateTime(timezone=True), nullable=True),
    )

    op.add_column(
        "items",
        sa.Column("path_c_bridge", sa.Boolean(), nullable=False, server_default="false"),
    )
    op.add_column(
        "items",
        sa.Column("path_b_bridge", sa.Boolean(), nullable=False, server_default="false"),
    )

    op.add_column(
        "users",
        sa.Column(
            "fraud_verification_override",
            sa.Boolean(),
            nullable=False,
            server_default="false",
        ),
    )
    op.add_column(
        "users",
        sa.Column("fraud_risk_score", sa.Integer(), nullable=False, server_default="0"),
    )
    op.add_column(
        "users",
        sa.Column("trust_score", sa.Integer(), nullable=False, server_default="0"),
    )

    # Tables are not recreated on downgrade — would require full schema restore

    op.add_column(
        "user_reports",
        sa.Column("context_conversation_id", sa.UUID(), nullable=True),
    )
