"""add embedding to topics

Revision ID: 6ffad026c8a0
Revises: 23824f661f08
Create Date: 2026-01-12 20:06:41.588648

"""

from typing import Sequence, Union

from sentence_transformers import SentenceTransformer
from sqlalchemy import text

from alembic import op

# revision identifiers, used by Alembic.
revision: str = "6ffad026c8a0"
down_revision: Union[str, None] = "23824f661f08"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.execute(text("ALTER TABLE plenartrend.topics ADD COLUMN IF NOT EXISTS embedding vector(384)"))

    # Themenliste
    topics_list = [
        "Migration & Asylpolitik",
        "Innere Sicherheit & Extremismus",
        "Renten- und Sozialpolitik",
        "Haushalt, Finanzen & Wirtschaft",
        "Kultur- und Bildungspolitik",
        "Gesellschaftliche Rechte & Selbstbestimmung",
        "Parlaments- und Verfahrensregeln",
        "Zukunft der NATO- und Verteidigungspolitik",
        "Abtreibungsrecht / reproduktive Rechte",
        "Parteipositionen nach der Bundestagswahl 2025",
    ]

    model = SentenceTransformer("sentence-transformers/all-MiniLM-L6-v2")
    embeddings = model.encode(topics_list)

    conn = op.get_bind()
    for topic, emb in zip(topics_list, embeddings):
        emb_str = "[" + ",".join(map(str, emb)) + "]"

        conn.execute(
            text(f"INSERT INTO plenartrend.topics (name, embedding) VALUES ('{topic}', '{emb_str}'::vector(384)) "),
        )


def downgrade() -> None:
    op.drop_column("plenartrend.topics", "embedding")
