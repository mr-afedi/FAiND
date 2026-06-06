"""admin_logs table and dispute resolution fields (Feature R)

Revision ID: r8a1b2c3d4e5
Revises: f1a2b3c4d5e7
Create Date: 2026-05-22

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
from sqlalchemy import inspect
from sqlalchemy.dialects import postgresql

revision: str = "r8a1b2c3d4e5"
down_revision: Union[str, None] = "f1a2b3c4d5e7"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None

admin_action_enum = postgresql.ENUM(
    "promote_admin",
    "demote_admin",
    "suspend_user",
    "unsuspend_user",
    "approve_claim",
    "reject_claim",
    "resolve_dispute",
    "remove_post",
    "force_close_post",
    "dismiss_report",
    "warn_user",
    "suppress_reporter",
    "confirm_fraud",
    "trust_adjustment",
    name="adminactiontype",
    create_type=False,
)


def _table_exists(name: str) -> bool:
    return name in inspect(op.get_bind()).get_table_names()


def _column_exists(table: str, column: str) -> bool:
    cols = inspect(op.get_bind()).get_columns(table)
    return any(c["name"] == column for c in cols)


def _index_exists(table: str, index_name: str) -> bool:
    indexes = inspect(op.get_bind()).get_indexes(table)
    return any(ix["name"] == index_name for ix in indexes)


def _fk_exists(table: str, fk_name: str) -> bool:
    fks = inspect(op.get_bind()).get_foreign_keys(table)
    return any(fk.get("name") == fk_name for fk in fks)


_ADMIN_LOG_COLUMNS = (
    "id",
    "admin_id",
    "action",
    "target_type",
    "target_id",
    "detail",
    "created_at",
)


def _admin_logs_schema_ok() -> bool:
    if not _table_exists("admin_logs"):
        return False
    return all(_column_exists("admin_logs", col) for col in _ADMIN_LOG_COLUMNS)


def _drop_admin_logs_if_present() -> None:
    if not _table_exists("admin_logs"):
        return
    for ix in inspect(op.get_bind()).get_indexes("admin_logs"):
        name = ix.get("name")
        if name:
            op.drop_index(name, table_name="admin_logs")
    op.drop_table("admin_logs")


def upgrade() -> None:
    admin_action_enum.create(op.get_bind(), checkfirst=True)

    # Recover from a partial/failed create (table name exists but columns differ).
    if _table_exists("admin_logs") and not _admin_logs_schema_ok():
        _drop_admin_logs_if_present()

    if not _table_exists("admin_logs"):
        op.create_table(
            "admin_logs",
            sa.Column("id", sa.UUID(), nullable=False),
            sa.Column("admin_id", sa.UUID(), nullable=True),
            sa.Column("action", admin_action_enum, nullable=False),
            sa.Column("target_type", sa.String(length=50), nullable=False),
            sa.Column("target_id", sa.UUID(), nullable=True),
            sa.Column("detail", postgresql.JSONB(astext_type=sa.Text()), nullable=False),
            sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
            sa.ForeignKeyConstraint(["admin_id"], ["users.id"], ondelete="SET NULL"),
            sa.PrimaryKeyConstraint("id"),
        )

    for idx_name, cols in (
        ("ix_admin_logs_action", ["action"]),
        ("ix_admin_logs_admin_id", ["admin_id"]),
        ("ix_admin_logs_created_at", ["created_at"]),
        ("ix_admin_logs_target_id", ["target_id"]),
    ):
        if all(_column_exists("admin_logs", col) for col in cols):
            if not _index_exists("admin_logs", idx_name):
                op.create_index(idx_name, "admin_logs", cols, unique=False)

    if not _column_exists("item_returns", "dispute_resolved_at"):
        op.add_column(
            "item_returns",
            sa.Column("dispute_resolved_at", sa.DateTime(timezone=True), nullable=True),
        )
    if not _column_exists("item_returns", "dispute_resolution_note"):
        op.add_column(
            "item_returns",
            sa.Column("dispute_resolution_note", sa.Text(), nullable=True),
        )
    if not _column_exists("item_returns", "dispute_resolved_by_id"):
        op.add_column(
            "item_returns",
            sa.Column("dispute_resolved_by_id", sa.UUID(), nullable=True),
        )
    if not _fk_exists("item_returns", "fk_item_returns_dispute_resolved_by"):
        op.create_foreign_key(
            "fk_item_returns_dispute_resolved_by",
            "item_returns",
            "users",
            ["dispute_resolved_by_id"],
            ["id"],
            ondelete="SET NULL",
        )


def downgrade() -> None:
    if _fk_exists("item_returns", "fk_item_returns_dispute_resolved_by"):
        op.drop_constraint("fk_item_returns_dispute_resolved_by", "item_returns", type_="foreignkey")
    if _column_exists("item_returns", "dispute_resolved_by_id"):
        op.drop_column("item_returns", "dispute_resolved_by_id")
    if _column_exists("item_returns", "dispute_resolution_note"):
        op.drop_column("item_returns", "dispute_resolution_note")
    if _column_exists("item_returns", "dispute_resolved_at"):
        op.drop_column("item_returns", "dispute_resolved_at")
    if _table_exists("admin_logs"):
        _drop_admin_logs_if_present()
    admin_action_enum.drop(op.get_bind(), checkfirst=True)
