"""add sentiment and topic to activity mappings

Revision ID: d4b657bc7eeb
Revises: 6ffad026c8a0
Create Date: 2026-01-12 21:54:01.741892

"""

from typing import Sequence, Union

import sqlalchemy as sa

from alembic import op

# revision identifiers, used by Alembic.
revision: str = "d4b657bc7eeb"
down_revision: Union[str, None] = "6ffad026c8a0"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table(
        "activity_mappings",
        sa.Column("id", sa.Integer, primary_key=True, autoincrement=True),
        sa.Column("activity_id", sa.Integer, nullable=False),
        sa.Column("topic_id", sa.Integer, nullable=True),
        sa.Column("sentiment_value", sa.Float, nullable=True),
        sa.Column("sentiment_reason", sa.Text, nullable=True),
    )


def downgrade() -> None:
    op.drop_table("activity_mappings")
