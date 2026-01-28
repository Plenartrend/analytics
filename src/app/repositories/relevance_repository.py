from typing import Optional

from sqlalchemy.ext.asyncio import AsyncSession

from ..model.model import Activity, ActivityMapping, ActivityRelevance
from ..utils.db import get_db


async def calculate_relevance_for_activity(protocol_id: int, transaction: Optional[AsyncSession] = None):
    from sqlalchemy import Float, cast, func, select
    from sqlalchemy.dialects.postgresql import insert

    counts_subq = (
        select(
            Activity.protocol_id.label("protocol_id"),
            ActivityMapping.topic_id.label("topic_id"),
            cast(func.count(), Float).label("topic_count"),
            func.sum(func.count()).over(partition_by=Activity.protocol_id).label("total_count"),
        )
        .join(
            Activity,
            Activity.id == ActivityMapping.activity_id,
        )
        .where(
            ActivityMapping.topic_id.isnot(None),
            Activity.protocol_id == protocol_id,
        )
        .group_by(
            Activity.protocol_id,
            ActivityMapping.topic_id,
        )
        .subquery()
    )

    stmt = (
        insert(ActivityRelevance)
        .from_select(
            ["protocol_id", "topic_id", "relevance"],
            select(
                counts_subq.c.protocol_id,
                counts_subq.c.topic_id,
                counts_subq.c.topic_count / counts_subq.c.total_count,
            ),
        )
        .on_conflict_do_update(
            index_elements=["protocol_id", "topic_id"],
            set_={
                "relevance": insert(ActivityRelevance).excluded.relevance,
            },
        )
    )

    if transaction:
        await transaction.execute(stmt)
    else:
        async with get_db() as db:
            await db.execute(stmt)
            await db.commit()
