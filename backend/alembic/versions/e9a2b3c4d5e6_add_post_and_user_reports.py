"""add post_reports, user_reports, reports_suppressed (Feature P)

Revision ID: e9a2b3c4d5e6
Revises: d7e1f04a8b12
Create Date: 2026-05-22

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

revision: str = "e9a2b3c4d5e6"
down_revision: Union[str, None] = "d7e1f04a8b12"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None

report_status_enum = postgresql.ENUM(
    "pending", "dismissed", "resolved", name="reportstatus", create_type=False
)
post_report_reason_enum = postgresql.ENUM(
    "fake_or_misleading",
    "suspicious_behavior",
    "inappropriate_content",
    "spam",
    "other",
    name="postreportreason",
    create_type=False,
)
user_report_reason_enum = postgresql.ENUM(
    "threatening_abusive",
    "suspected_fraud",
    "harassment",
    "impersonation",
    "other",
    name="userreportreason",
    create_type=False,
)
admin_report_action_enum = postgresql.ENUM(
    "dismiss",
    "remove_post",
    "warn_user",
    "suspend_user",
    name="adminreportaction",
    create_type=False,
)


def upgrade() -> None:
    report_status_enum.create(op.get_bind(), checkfirst=True)
    post_report_reason_enum.create(op.get_bind(), checkfirst=True)
    user_report_reason_enum.create(op.get_bind(), checkfirst=True)
    admin_report_action_enum.create(op.get_bind(), checkfirst=True)

    op.add_column(
        "users",
        sa.Column("reports_suppressed", sa.Boolean(), nullable=False, server_default="false"),
    )
    op.alter_column("users", "reports_suppressed", server_default=None)

    op.create_table(
        "post_reports",
        sa.Column("id", sa.UUID(), nullable=False),
        sa.Column("university_id", sa.UUID(), nullable=False),
        sa.Column("reporter_id", sa.UUID(), nullable=False),
        sa.Column("item_id", sa.UUID(), nullable=False),
        sa.Column("reason", post_report_reason_enum, nullable=False),
        sa.Column("detail_text", sa.String(length=200), nullable=True),
        sa.Column("status", report_status_enum, nullable=False),
        sa.Column("auto_escalated", sa.Boolean(), nullable=False),
        sa.Column("admin_action", admin_report_action_enum, nullable=True),
        sa.Column("resolved_by_id", sa.UUID(), nullable=True),
        sa.Column("resolved_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.ForeignKeyConstraint(["item_id"], ["items.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["reporter_id"], ["users.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["resolved_by_id"], ["users.id"], ondelete="SET NULL"),
        sa.ForeignKeyConstraint(["university_id"], ["universities.id"], ondelete="RESTRICT"),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("reporter_id", "item_id", name="uq_post_reports_reporter_item"),
    )
    op.create_index(op.f("ix_post_reports_item_id"), "post_reports", ["item_id"], unique=False)
    op.create_index(op.f("ix_post_reports_reporter_id"), "post_reports", ["reporter_id"], unique=False)
    op.create_index(op.f("ix_post_reports_university_id"), "post_reports", ["university_id"], unique=False)

    op.create_table(
        "user_reports",
        sa.Column("id", sa.UUID(), nullable=False),
        sa.Column("university_id", sa.UUID(), nullable=False),
        sa.Column("reporter_id", sa.UUID(), nullable=False),
        sa.Column("reported_user_id", sa.UUID(), nullable=False),
        sa.Column("reason", user_report_reason_enum, nullable=False),
        sa.Column("detail_text", sa.String(length=200), nullable=True),
        sa.Column("context_conversation_id", sa.UUID(), nullable=True),
        sa.Column("status", report_status_enum, nullable=False),
        sa.Column("auto_escalated", sa.Boolean(), nullable=False),
        sa.Column("admin_action", admin_report_action_enum, nullable=True),
        sa.Column("resolved_by_id", sa.UUID(), nullable=True),
        sa.Column("resolved_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.ForeignKeyConstraint(["context_conversation_id"], ["conversations.id"], ondelete="SET NULL"),
        sa.ForeignKeyConstraint(["reported_user_id"], ["users.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["reporter_id"], ["users.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["resolved_by_id"], ["users.id"], ondelete="SET NULL"),
        sa.ForeignKeyConstraint(["university_id"], ["universities.id"], ondelete="RESTRICT"),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint(
            "reporter_id", "reported_user_id", name="uq_user_reports_reporter_target"
        ),
    )
    op.create_index(op.f("ix_user_reports_reported_user_id"), "user_reports", ["reported_user_id"], unique=False)
    op.create_index(op.f("ix_user_reports_reporter_id"), "user_reports", ["reporter_id"], unique=False)
    op.create_index(op.f("ix_user_reports_university_id"), "user_reports", ["university_id"], unique=False)


def downgrade() -> None:
    op.drop_index(op.f("ix_user_reports_university_id"), table_name="user_reports")
    op.drop_index(op.f("ix_user_reports_reporter_id"), table_name="user_reports")
    op.drop_index(op.f("ix_user_reports_reported_user_id"), table_name="user_reports")
    op.drop_table("user_reports")
    op.drop_index(op.f("ix_post_reports_university_id"), table_name="post_reports")
    op.drop_index(op.f("ix_post_reports_reporter_id"), table_name="post_reports")
    op.drop_index(op.f("ix_post_reports_item_id"), table_name="post_reports")
    op.drop_table("post_reports")
    op.drop_column("users", "reports_suppressed")
    admin_report_action_enum.drop(op.get_bind(), checkfirst=True)
    user_report_reason_enum.drop(op.get_bind(), checkfirst=True)
    post_report_reason_enum.drop(op.get_bind(), checkfirst=True)
    report_status_enum.drop(op.get_bind(), checkfirst=True)
