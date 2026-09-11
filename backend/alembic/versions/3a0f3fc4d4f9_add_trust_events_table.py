"""add_trust_events_table

Revision ID: 3a0f3fc4d4f9
Revises: 1e779e6de077
Create Date: 2026-05-20 19:25:29.349892

No earlier revision creates trust_events. This file originally only
ALTERed a table that existed on some developer databases. Fresh clones
must CREATE the post-restructure schema; databases that already have the
legacy table still follow the original ALTER path.

The table is dropped later by x1w2c3d4e5f6 (V5 W1 removal pass).
"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
from sqlalchemy import inspect
from sqlalchemy.dialects import postgresql

# revision identifiers, used by Alembic.
revision: str = '3a0f3fc4d4f9'
down_revision: Union[str, None] = '1e779e6de077'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None

_TRUST_REASONS = (
    'found_item_posted', 'successful_return',
    'failed_verification_2nd', 'failed_verification_3rd',
    'false_claim_confirmed', 'fraud_confirmed',
    'user_report_received', 'admin_adjustment',
)

trusteventreason = postgresql.ENUM(
    *_TRUST_REASONS,
    name='trusteventreason',
    create_type=False,
)


def _table_exists(name: str) -> bool:
    return name in inspect(op.get_bind()).get_table_names()


def _column_exists(table: str, column: str) -> bool:
    return any(c["name"] == column for c in inspect(op.get_bind()).get_columns(table))


def _index_exists(table: str, index_name: str) -> bool:
    return any(ix.get("name") == index_name for ix in inspect(op.get_bind()).get_indexes(table))


def _create_trust_events_table() -> None:
    op.create_table(
        'trust_events',
        sa.Column('id', sa.UUID(), nullable=False),
        sa.Column('user_id', sa.UUID(), nullable=False),
        sa.Column('reason', trusteventreason, nullable=False),
        sa.Column('delta', sa.Integer(), nullable=False),
        sa.Column('reference_id', sa.UUID(), nullable=True),
        sa.Column('applied_by_id', sa.UUID(), nullable=True),
        sa.Column('created_at', sa.DateTime(timezone=True), nullable=False),
        sa.ForeignKeyConstraint(['applied_by_id'], ['users.id'], ondelete='SET NULL'),
        sa.ForeignKeyConstraint(['user_id'], ['users.id'], ondelete='CASCADE'),
        sa.PrimaryKeyConstraint('id'),
    )
    op.create_index('ix_trust_events_user_id', 'trust_events', ['user_id'], unique=False)


def upgrade() -> None:
    trusteventreason.create(op.get_bind(), checkfirst=True)

    if not _table_exists('trust_events'):
        _create_trust_events_table()
        return

    # Already on the post-restructure schema (or re-run after a partial apply).
    if _column_exists('trust_events', 'delta') and not _column_exists('trust_events', 'trust_delta'):
        return

    # Legacy table from a pre-alembic schema: restructure in place.
    op.execute("DELETE FROM trust_events")

    if not _column_exists('trust_events', 'delta'):
        op.add_column('trust_events', sa.Column('delta', sa.Integer(), nullable=False, server_default='0'))
    if not _column_exists('trust_events', 'reference_id'):
        op.add_column('trust_events', sa.Column('reference_id', sa.UUID(), nullable=True))
    if not _column_exists('trust_events', 'applied_by_id'):
        op.add_column('trust_events', sa.Column('applied_by_id', sa.UUID(), nullable=True))

    op.execute(
        "ALTER TABLE trust_events ALTER COLUMN reason TYPE trusteventreason USING reason::trusteventreason"
    )
    op.alter_column('trust_events', 'delta', server_default=None)
    op.alter_column(
        'trust_events',
        'created_at',
        existing_type=postgresql.TIMESTAMP(),
        type_=sa.DateTime(timezone=True),
        existing_nullable=False,
    )

    if _index_exists('trust_events', 'ix_trust_events_created_at'):
        op.drop_index('ix_trust_events_created_at', table_name='trust_events')
    if _index_exists('trust_events', 'ix_trust_events_id'):
        op.drop_index('ix_trust_events_id', table_name='trust_events')

    op.create_foreign_key(None, 'trust_events', 'users', ['applied_by_id'], ['id'], ondelete='SET NULL')
    op.create_foreign_key(None, 'trust_events', 'users', ['user_id'], ['id'], ondelete='CASCADE')

    for col in (
        'trust_delta', 'note', 'fraud_risk_after',
        'related_entity_id', 'fraud_risk_delta', 'trust_score_after',
    ):
        if _column_exists('trust_events', col):
            op.drop_column('trust_events', col)


def downgrade() -> None:
    if not _table_exists('trust_events'):
        trusteventreason.drop(op.get_bind(), checkfirst=True)
        return

    if _column_exists('trust_events', 'trust_score_after'):
        trusteventreason.drop(op.get_bind(), checkfirst=True)
        return

    op.add_column('trust_events', sa.Column('trust_score_after', sa.INTEGER(), autoincrement=False, nullable=False))
    op.add_column('trust_events', sa.Column('fraud_risk_delta', sa.DOUBLE_PRECISION(precision=53), server_default=sa.text("'0'::double precision"), autoincrement=False, nullable=False))
    op.add_column('trust_events', sa.Column('related_entity_id', sa.VARCHAR(length=36), autoincrement=False, nullable=True))
    op.add_column('trust_events', sa.Column('fraud_risk_after', sa.DOUBLE_PRECISION(precision=53), autoincrement=False, nullable=False))
    op.add_column('trust_events', sa.Column('note', sa.TEXT(), autoincrement=False, nullable=True))
    op.add_column('trust_events', sa.Column('trust_delta', sa.INTEGER(), server_default=sa.text('0'), autoincrement=False, nullable=False))
    op.create_index('ix_trust_events_id', 'trust_events', ['id'], unique=False)
    op.create_index('ix_trust_events_created_at', 'trust_events', ['created_at'], unique=False)
    op.alter_column('trust_events', 'created_at',
               existing_type=sa.DateTime(timezone=True),
               type_=postgresql.TIMESTAMP(),
               existing_nullable=False)
    op.alter_column('trust_events', 'reason',
               existing_type=sa.Enum(*_TRUST_REASONS, name='trusteventreason'),
               type_=sa.VARCHAR(length=100),
               existing_nullable=False)
    if _column_exists('trust_events', 'applied_by_id'):
        op.drop_column('trust_events', 'applied_by_id')
    if _column_exists('trust_events', 'reference_id'):
        op.drop_column('trust_events', 'reference_id')
    if _column_exists('trust_events', 'delta'):
        op.drop_column('trust_events', 'delta')
    trusteventreason.drop(op.get_bind(), checkfirst=True)
