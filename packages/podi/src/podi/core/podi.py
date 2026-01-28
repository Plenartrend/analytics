import asyncio
import datetime
import inspect
import logging
import traceback
from typing import Any, AsyncGenerator, Callable, List

from sqlalchemy import GenerativeSelect, and_, delete, exists, func, or_, select, text, update
from sqlalchemy.dialects.postgresql import insert
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import aliased

from .. import Lifecycle, Router
from ..config.config import PodiConfig
from ..dclasses import Event
from ..model.model import Activity, ActivityLatch, HashrrHeartbeat, HashrrInstance, PrintedPaper, Protocol, Role
from ..utils.db import get_db_generator

LOGGER = logging.getLogger("podi")


def dispatch_event(routes: dict[str, Callable]):
    async def wrapper(message: Any, session: AsyncSession, state: Any):
        to_object = Event.from_dict(message)
        LOGGER.log(logging.INFO, f"Request to {to_object.event}")
        params = inspect.signature(routes[to_object.event]).parameters
        kwargs = {}
        if "session" in params:
            kwargs["session"] = session
        if "state" in params:
            kwargs["state"] = state

        await routes[to_object.event](to_object.data, **kwargs)

    return wrapper


def collect_routes(routes_list: List[Router]):
    routes = {}
    for router in routes_list:
        for key in router._store.keys():
            routes[key] = router._store[key]
    return routes


def collect_lifecycle(lifecycle_list: List[Lifecycle]):
    lifecycle = {}
    for life in lifecycle_list:
        for key in life._store.keys():
            lifecycle[key] = life._store[key]
    return lifecycle


async def find_activites_stmt(key, length, settings) -> GenerativeSelect:
    outer_activity_alias = aliased(Activity)

    activity_latch_exists = exists(
        select(1).select_from(ActivityLatch).where(ActivityLatch.activity_id == outer_activity_alias.id)
    ).correlate(Activity)

    activity_latch_null_instance_exists = exists(
        select(1)
        .select_from(ActivityLatch)
        .where(
            ActivityLatch.activity_id == outer_activity_alias.id,
            ActivityLatch.hasharr_instance_id.is_(None),
        )
    ).correlate(Activity)

    working_with_fresh_heartbeat_exists = exists(
        select(1)
        .select_from(ActivityLatch)
        .join(
            HashrrInstance,
            ActivityLatch.hasharr_instance_id == HashrrInstance.id,
        )
        .join(
            HashrrHeartbeat,
            HashrrHeartbeat.hashrr_instance_id == HashrrInstance.id,
        )
        .where(
            ActivityLatch.activity_id == outer_activity_alias.id,
            ActivityLatch.latch == "WORKING",
            HashrrHeartbeat.heartbeat >= func.now() - text("INTERVAL '30 seconds'"),
        )
    )

    finished_latch_exists = exists(
        select(1)
        .select_from(ActivityLatch)
        .where(
            ActivityLatch.activity_id == outer_activity_alias.id,
            ActivityLatch.latch == "FINISHED",
        )
    )

    text_is_long_enough = exists(
        select(1)
        .select_from(Activity)
        .outerjoin(PrintedPaper, PrintedPaper.id == Activity.printed_paper_id)
        .outerjoin(Protocol, Protocol.id == Activity.protocol_id)
        .where(
            or_(
                and_(
                    Activity.id == outer_activity_alias.id,
                    Activity.document_type == "protocol",
                    Activity.text.isnot(None),
                    Activity.text != "",
                    Activity.text != "[NoTextAvailable]",
                    Protocol.date >= datetime.datetime.fromisoformat(settings.PROCESS_START_DATE).date(),
                    func.length(Activity.text) > 1000,
                ),
                and_(
                    Activity.id == outer_activity_alias.id,
                    Activity.document_type == "printedPaper",
                    PrintedPaper.text.isnot(None),
                    PrintedPaper.text != "",
                    PrintedPaper.text != "[NoTextAvailable]",
                    PrintedPaper.date >= datetime.datetime.fromisoformat(settings.PROCESS_START_DATE).date(),
                    func.length(PrintedPaper.text) > 1000,
                ),
            )
        )
    )

    stmt = (
        select(outer_activity_alias)
        .where(
            outer_activity_alias.id % length == key,
            outer_activity_alias.document_type != "printedPaper",
            ~finished_latch_exists,
            text_is_long_enough,
            or_(
                ~activity_latch_exists,
                activity_latch_null_instance_exists,
                working_with_fresh_heartbeat_exists,
            ),
        )
        .order_by(outer_activity_alias.created)
    )
    return stmt


async def dispatch_to_protocols(activity: Activity, db: AsyncSession):
    stmt = select(Role).where(Role.id == activity.role_id)

    res = await db.execute(stmt)
    role: Role = res.scalars().first()

    stmt = select(Protocol).where(Protocol.id == activity.protocol_id)

    res = await db.execute(stmt)
    protocol: Protocol = res.scalars().first()

    LOGGER.info(f"Calling analyseProtocolEvent for activity id {activity.id}")

    event_type = {
        "event": "analyseProtocolEvent",
        "data": {
            "id": activity.id,
            "speech": activity.text,
            "person_id": role.person_id,
            "protocol_id": protocol.id,
            "speech_date": protocol.date,
        },
    }

    await db.commit()

    return event_type


async def dispatch_to_printed_papers(activities: list[Activity], activity: Activity, db: AsyncSession):
    stmt = select(PrintedPaper).where(PrintedPaper.id == activity.printed_paper_id)

    res = await db.execute(stmt)

    printed_paper: PrintedPaper = res.scalars().first()

    LOGGER.info(f"Calling analysePrintedPaperEvent for activity id {activity.id}")

    event_type = {
        "event": "analysePrintedPaperEvent",
        "data": {
            "id": activity.printed_paper_id,
            "activity_ids": [act.id for act in activities],
            "title": printed_paper.title,
            "text": printed_paper.text,
        },
    }

    await db.commit()

    return event_type


class Podi:
    def __init__(self, config: PodiConfig, routes: List[Router], lifecycle: List[Lifecycle], state: Any = None) -> None:
        self.config = config
        self.routes = routes
        self.lifecycle = lifecycle
        self.state = state

    async def run(self):
        get_db: Callable[[], AsyncGenerator[AsyncSession, None]] = get_db_generator(self.config.settings)
        routes = collect_routes(self.routes)
        lifecycles = collect_lifecycle(self.lifecycle)

        if "on_open" in lifecycles:
            await lifecycles["on_open"]()

        while True:
            try:
                async with get_db() as db:
                    db: AsyncSession
                    key, length, hasharr_id = await self.state.distributed_key_function()

                    stmt = await find_activites_stmt(key, length, self.config.settings)

                    transaction = await db.begin()

                    res = await db.execute(stmt)

                    activity: Activity = res.scalars().first()

                    if activity is None:
                        await transaction.commit()
                        await asyncio.sleep(0.3)

                    elif activity.document_type == "printedPaper":
                        stmt = select(Activity).where(Activity.printed_paper_id == activity.printed_paper_id)

                        res = await db.execute(stmt)
                        activities: list[Activity] = list(res.scalars().all())
                        activity_ids: list[int] = [act.id for act in activities]

                        promises = []
                        for act in activities:
                            stmt = (
                                insert(ActivityLatch)
                                .values(
                                    activity_id=act.id,
                                    hasharr_instance_id=hasharr_id,
                                )
                                .on_conflict_do_update(
                                    index_elements=[ActivityLatch.activity_id],
                                    set_={
                                        "hasharr_instance_id": hasharr_id,
                                    },
                                )
                            )

                            promises.append(db.execute(stmt))

                        await asyncio.gather(*promises)
                        await transaction.commit()

                        try:
                            async with db.begin():
                                event_type = await dispatch_to_printed_papers(activities, activity, db)

                                await dispatch_event(routes)(event_type, db, self.state)

                                for act in activities:
                                    stmt = (
                                        update(ActivityLatch)
                                        .where(ActivityLatch.activity_id == act.id)
                                        .values(
                                            hasharr_instance_id=hasharr_id,
                                            latch="FINISHED",
                                        )
                                    )
                                    await db.execute(stmt)

                        except Exception:
                            async with db.begin():
                                promises = []
                                for id in activity_ids:
                                    stmt = delete(ActivityLatch).where(ActivityLatch.activity_id == id)
                                    promises.append(db.execute(stmt))

                                await asyncio.gather(*promises)

                    elif activity.document_type == "protocol":
                        stmt = (
                            insert(ActivityLatch)
                            .values(
                                activity_id=activity.id,
                                hasharr_instance_id=hasharr_id,
                            )
                            .on_conflict_do_update(
                                index_elements=[ActivityLatch.activity_id],
                                set_={
                                    "hasharr_instance_id": hasharr_id,
                                },
                            )
                        )

                        activity_id = activity.id

                        await db.execute(stmt)
                        await transaction.commit()

                        event_type = await dispatch_to_protocols(activity, db)

                        try:
                            async with db.begin():
                                await dispatch_event(routes)(event_type, db, self.state)

                                stmt = (
                                    update(ActivityLatch)
                                    .where(ActivityLatch.activity_id == activity.id)
                                    .values(
                                        hasharr_instance_id=hasharr_id,
                                        latch="FINISHED",
                                    )
                                )

                                await db.execute(stmt)
                        except Exception:
                            async with db.begin():
                                stmt = delete(ActivityLatch).where(ActivityLatch.activity_id == activity_id)
                                await db.execute(stmt)
                    else:
                        await transaction.commit()

            except Exception as e:
                if isinstance(e, _KadiCloseException):
                    if "on_close" in lifecycles:
                        await lifecycles["on_close"]()
                    break
                elif "on_error" in lifecycles:
                    await lifecycles["on_error"](e)
                else:
                    traceback.print_exc()
                    LOGGER.error(f"Error processing message: {e}")


def close():
    raise _KadiCloseException


class _KadiCloseException(Exception):
    pass
