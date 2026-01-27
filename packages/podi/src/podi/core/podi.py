import asyncio
import inspect
import logging
import traceback
from typing import Any, AsyncGenerator, Callable, List

from sqlalchemy import and_, exists, func, or_, select, text
from sqlalchemy.ext.asyncio import AsyncSession

from .. import Lifecycle, Router
from ..config.config import PodiConfig
from ..dclasses import Event
from ..model.model import Activity, ActivityLatch, HashrrHeartbeat, HashrrInstance, PrintedPaper, Protocol, Role
from ..utils.db import get_db_generator

LOGGER = logging.getLogger("podi")


def dispatch_event(routes: dict[str:Callable]):
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

                    activity_latch_exists = exists(
                        select(1).select_from(ActivityLatch).where(ActivityLatch.activity_id == Activity.id)
                    ).correlate(Activity)

                    activity_latch_null_instance_exists = exists(
                        select(1)
                        .select_from(ActivityLatch)
                        .where(
                            ActivityLatch.activity_id == Activity.id,
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
                            ActivityLatch.activity_id == Activity.id,
                            ActivityLatch.latch == "WORKING",
                            HashrrHeartbeat.heartbeat >= func.now() - text("INTERVAL '30 seconds'"),
                        )
                    ).correlate(Activity)

                    finished_latch_exists = exists(
                        select(1)
                        .select_from(ActivityLatch)
                        .where(
                            ActivityLatch.activity_id == Activity.id,
                            ActivityLatch.latch == "FINISHED",
                        )
                    ).correlate(Activity)

                    stmt = (
                        select(Activity)
                        .where(
                            Activity.id % length == key,
                            or_(
                                ~activity_latch_exists,
                                activity_latch_null_instance_exists,
                                and_(
                                    working_with_fresh_heartbeat_exists,
                                    ~finished_latch_exists,
                                ),
                            ),
                        )
                        .order_by(Activity.created.asc())
                        .with_for_update(skip_locked=True)
                    )

                    res = await db.execute(stmt)

                    activity: Activity = res.scalars().first()

                    if activity is None:
                        await asyncio.sleep(0.3)

                    elif len(activity.text) < 50:
                        LOGGER.log(logging.WARNING, f"Activity {activity.id} text too short, skipping analysis.")

                        latch = ActivityLatch(activity_id=activity.id, hasharr_instance_id=hasharr_id, latch="FINISHED")
                        db.add(latch)

                    elif activity.document_type == "printedPaper":
                        latch = ActivityLatch(activity_id=activity.id, hasharr_instance_id=hasharr_id)
                        db.add(latch)
                        await db.commit()

                        stmt = select(PrintedPaper).where(PrintedPaper.id == activity.printed_paper_id)

                        res = await db.execute(stmt)

                        printed_paper: PrintedPaper = res.scalars().first()

                        LOGGER.info(f"Calling analysePrintedPaperEvent for activity id {activity.id}")

                        event_type = {
                            "event": "analysePrintedPaperEvent",
                            "data": {"id": activity.id, "title": printed_paper.title, "speech": printed_paper.text},
                        }

                        await dispatch_event(routes)(event_type, db, self.state)

                        latch = ActivityLatch(activity_id=activity.id, hasharr_instance_id=hasharr_id, latch="FINISHED")
                        db.add(latch)

                    elif activity.document_type == "protocol":
                        latch = ActivityLatch(activity_id=activity.id, hasharr_instance_id=hasharr_id)
                        db.add(latch)
                        await db.commit()

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

                        await dispatch_event(routes)(event_type, db, self.state)

                        latch = ActivityLatch(activity_id=activity.id, hasharr_instance_id=hasharr_id, latch="FINISHED")
                        db.add(latch)

                    await db.commit()
                continue

            except Exception as e:
                if isinstance(e, _KadiCloseException):
                    break
                elif "on_error" in lifecycles:
                    await lifecycles["on_error"](e)
                else:
                    traceback.print_exc()
                    LOGGER.error(f"Error processing message: {e}")
            finally:
                if "on_close" in lifecycles:
                    await lifecycles["on_close"]()


def close():
    raise _KadiCloseException


class _KadiCloseException(Exception):
    pass
