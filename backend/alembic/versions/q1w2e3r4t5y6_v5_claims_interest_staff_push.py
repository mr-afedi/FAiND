"""V5 — item interests, claim rejected_at, staff push subscriptions

Revision ID: q1w2e3r4t5y6
Revises: n8w9a0b1c2d3
Create Date: 2026-05-22

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


revision: str = "q1w2e3r4t5y6"
down_revision: Union[str, None] = "n8w9a0b1c2d3"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table(
        "item_interests",
        sa.Column("id", sa.UUID(), nullable=False),
        sa.Column("user_id", sa.UUID(), nullable=False),
        sa.Column("found_item_id", sa.UUID(), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.ForeignKeyConstraint(["user_id"], ["users.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["found_item_id"], ["items.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("user_id", "found_item_id", name="uq_item_interest_user_item"),
    )
    op.create_index("ix_item_interests_user_id", "item_interests", ["user_id"])
    op.create_index("ix_item_interests_found_item_id", "item_interests", ["found_item_id"])

    op.add_column("claims", sa.Column("rejected_at", sa.DateTime(timezone=True), nullable=True))

    op.add_column(
        "authorities",
        sa.Column("push_notifications_enabled", sa.Boolean(), nullable=False, server_default="false"),
    )
    op.add_column(
        "supervisors",
        sa.Column("push_notifications_enabled", sa.Boolean(), nullable=False, server_default="false"),
    )

    op.create_table(
        "staff_push_subscriptions",
        sa.Column("id", sa.UUID(), nullable=False),
        sa.Column(
            "staff_type",
            sa.Enum("authority", "supervisor", "admin", name="staffpushtype"),
            nullable=False,
        ),
        sa.Column("staff_id", sa.UUID(), nullable=False),
        sa.Column("endpoint", sa.Text(), nullable=False),
        sa.Column("p256dh", sa.String(length=512), nullable=False),
        sa.Column("auth", sa.String(length=128), nullable=False),
        sa.Column("is_active", sa.Boolean(), nullable=False, server_default="true"),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint(
            "staff_type", "staff_id", "endpoint", name="uq_staff_push_endpoint"
        ),
    )
    op.create_index(
        "ix_staff_push_subscriptions_staff",
        "staff_push_subscriptions",
        ["staff_type", "staff_id"],
    )

    op.create_table(
        "supervisor_alerts",
        sa.Column("id", sa.UUID(), nullable=False),
        sa.Column("supervisor_id", sa.UUID(), nullable=False),
        sa.Column(
            "alert_type",
            sa.Enum(
                "new_item_incoming",
                "finder_marked_dropoff",
                "new_claim",
                "owner_inquiry",
                "item_overdue",
                "admin_action",
                "handover_complete",
                "item_removed",
                "drop_point_closed",
                name="supervisoralerttype",
            ),
            nullable=False,
        ),
        sa.Column("title", sa.String(length=200), nullable=False),
        sa.Column("body", sa.Text(), nullable=False),
        sa.Column("link", sa.String(length=500), nullable=True),
        sa.Column("reference_id", sa.UUID(), nullable=True),
        sa.Column("read", sa.Boolean(), nullable=False, server_default="false"),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.ForeignKeyConstraint(["supervisor_id"], ["supervisors.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("ix_supervisor_alerts_supervisor_id", "supervisor_alerts", ["supervisor_id"])


def downgrade() -> None:
    op.drop_index("ix_supervisor_alerts_supervisor_id", table_name="supervisor_alerts")
    op.drop_table("supervisor_alerts")
    op.drop_index("ix_staff_push_subscriptions_staff", table_name="staff_push_subscriptions")
    op.drop_table("staff_push_subscriptions")
    op.drop_column("supervisors", "push_notifications_enabled")
    op.drop_column("authorities", "push_notifications_enabled")
    op.drop_column("claims", "rejected_at")
    op.drop_index("ix_item_interests_found_item_id", table_name="item_interests")
    op.drop_index("ix_item_interests_user_id", table_name="item_interests")
    op.drop_table("item_interests")
    op.execute("DROP TYPE IF EXISTS staffpushtype")
    op.execute("DROP TYPE IF EXISTS supervisoralerttype")
