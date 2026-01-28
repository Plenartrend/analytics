"""Add printed paper result table

Revision ID: 9d408d054f1b
Revises: fcb6b3d04486
Create Date: 2026-01-28 16:44:18.236762

"""

from typing import Sequence, Union

import sqlalchemy as sa

from alembic import op

# revision identifiers, used by Alembic.
revision: str = "9d408d054f1b"
down_revision: Union[str, None] = "fcb6b3d04486"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table(
        "printed_paper_mappings",
        sa.Column("id", sa.Integer, primary_key=True, autoincrement=True),
        sa.Column("printed_papers_id", sa.Integer, nullable=False),
        sa.Column("topic_id", sa.Integer, nullable=True),
        sa.Column("sentiment_value", sa.Float, nullable=True),
        sa.Column("sentiment_reason", sa.Text, nullable=True),
    )


def downgrade() -> None:
    op.drop_table("printed_paper_mappings")
