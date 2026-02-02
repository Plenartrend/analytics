from datetime import datetime

from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from ..model.model import Activity, ActivityMapping, Protocol, Role


async def get_activity_cnt_after(person_id: int, date: datetime, session: AsyncSession) -> int:
    stmt = select(func.count(Activity.id)).where(
        ActivityMapping.activity_id == Activity.id,
        Activity.api_updated <= date,
        Activity.document_type == "protocol",
        Activity.role_id == Role.id,
        Role.person_id == person_id,
    )

    result = await session.execute(stmt)
    return result.scalar_one()


async def get_activities(person_id: int, date: datetime, session: AsyncSession) -> list[Activity]:
    stmt = select(Activity).where(
        Protocol.id == Activity.protocol_id,
        Protocol.date >= date,
        Activity.document_type == "protocol",
        Activity.role_id == Role.id,
        Role.person_id == person_id,
    )

    result = await session.execute(stmt)
    all = result.scalars().all()
    return all
