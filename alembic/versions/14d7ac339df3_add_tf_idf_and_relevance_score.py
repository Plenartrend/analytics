"""Add TF-IDF and relevance score

Revision ID: 14d7ac339df3
Revises: d4b657bc7eeb
Create Date: 2026-01-26 21:09:00.862397

"""

from typing import Sequence, Union

import sqlalchemy as sa

from alembic import op

# revision identifiers, used by Alembic.
revision: str = "14d7ac339df3"
down_revision: Union[str, None] = "d4b657bc7eeb"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table(
        "activity_tfidf",
        sa.Column("person_id", sa.Integer, primary_key=True),
        sa.Column("tfidf_vector", sa.Text, nullable=False),
    )
    op.create_table(
        "activity_relevance",
        sa.Column("protocol_id", sa.Integer, primary_key=True),
        sa.Column("topic_id", sa.Integer, primary_key=True),
        sa.Column("relevance", sa.Float, nullable=False),
    )
    op.create_index(
        "uq_activity_latch_finished",
        "activity_latches",
        ["activity_id"],
        unique=True,
        postgresql_where=sa.text("latch = 'FINISHED'"),
    )


def downgrade() -> None:
    op.drop_table("activity_relevance")
    op.drop_table("activity_tfidf")

    op.drop_index("uq_activity_latch_finished", table_name="activity_latches")
