"""Add constraint on insert latch

Revision ID: fcb6b3d04486
Revises: 14d7ac339df3
Create Date: 2026-01-28 01:27:33.316029

"""

from typing import Sequence, Union

import sqlalchemy as sa

from alembic import op

# revision identifiers, used by Alembic.
revision: str = "fcb6b3d04486"
down_revision: Union[str, None] = "14d7ac339df3"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.drop_index("uq_activity_latch_finished", table_name="activity_latches")

    op.create_unique_constraint(
        "uq_activity_latch",
        "activity_latches",
        ["activity_id"],
    )


def downgrade() -> None:
    op.create_index(
        "uq_activity_latch_finished",
        "activity_latches",
        ["activity_id"],
        unique=True,
        postgresql_where=sa.text("latch = 'FINISHED'"),
    )
