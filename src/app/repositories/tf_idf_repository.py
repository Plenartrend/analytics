from typing import Optional

from sqlalchemy.dialects.postgresql import insert
from sqlalchemy.ext.asyncio import AsyncSession

from ..model.model import ActivityTfidf
from ..utils.db import get_db


async def insert_tfidf(person_id: int, tfidf_vector: str, transaction: Optional[AsyncSession] = None):
    stmt = (
        insert(ActivityTfidf)
        .values(person_id=person_id, tfidf_vector=tfidf_vector)
        .on_conflict_do_update(
            index_elements=["person_id"], set_={"tfidf_vector": insert(ActivityTfidf).excluded.tfidf_vector}
        )
    )

    if transaction:
        await transaction.execute(stmt)
    else:
        async with get_db() as db:
            db: AsyncSession
            await db.execute(stmt)
            await db.commit()
