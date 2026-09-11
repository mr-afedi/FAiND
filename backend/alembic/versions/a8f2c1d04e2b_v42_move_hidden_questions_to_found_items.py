"""v42_move_hidden_questions_to_found_items

V4.2: Hidden verification Q&A belong on found items (finder sets), not lost items.
Removes legacy rows tied to lost-item posts. Table shape unchanged (item_hidden_questions).

Revision ID: a8f2c1d04e2b
Revises: 5c46713d9400
Create Date: 2026-05-23

"""
from typing import Sequence, Union

from alembic import op

revision: str = "a8f2c1d04e2b"
down_revision: Union[str, None] = "5c46713d9400"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.execute(
        """
        DELETE FROM item_hidden_questions
        WHERE item_id IN (
            SELECT id FROM items WHERE item_type = 'lost'
        )
        """
    )


def downgrade() -> None:
    # Data migration — lost-item questions cannot be restored
    pass
