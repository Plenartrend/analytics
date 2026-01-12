import asyncio
import inspect
import logging
import traceback
from typing import Any, Callable, List

from sqlalchemy import exists, func, or_, select, text
from sqlalchemy.ext.asyncio import AsyncSession

from .. import Lifecycle, Router
from ..config.config import PodiConfig
from ..dclasses import Event
from ..model.model import Activity, ActivityLatch, HashrrHeartbeat, HashrrInstance
from ..utils.db import get_db

LOGGER = logging.getLogger("podi")


def dispatch_event(routes: dict[str:Callable]):
    async def wrapper(message: Any, state: Any):
        to_object = Event.from_dict(message)
        LOGGER.log(logging.INFO, f"Request to {to_object.event}")
        params = inspect.signature(routes[to_object.event]).parameters
        kwargs = {}
        if "state" in params:
            kwargs["state"] = state
            await routes[to_object.event](to_object.data, **kwargs)
        else:
            await routes[to_object.event](to_object.data)

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
        routes = collect_routes(self.routes)
        lifecycles = collect_lifecycle(self.lifecycle)

        while True:
            async with get_db(self.config.settings) as db:
                db: AsyncSession
                if "on_open" in lifecycles:
                    await lifecycles["on_open"]()
                    try:
                        key, length, hasharr_id = await self.state.distributed_key_function()
                        stmt = (
                            select(Activity)
                            .where(
                                Activity.id % length == key,
                                or_(
                                    ~exists().where(Activity.id == ActivityLatch.activity_id),
                                    exists().where(
                                        Activity.id == ActivityLatch.activity_id,
                                        ActivityLatch.hasharr_instance_id is None,
                                    ),
                                    exists().where(
                                        Activity.id == ActivityLatch.activity_id,
                                        ActivityLatch.hasharr_instance_id == HashrrInstance.id,
                                        HashrrInstance.id == HashrrHeartbeat.hashrr_instance_id,
                                        ActivityLatch.latch == "WORKING",
                                        HashrrHeartbeat.heartbeat >= func.now() - text("INTERVAL '30 seconds'"),
                                    ),
                                ),
                            )
                            .order_by(Activity.created.asc())
                        )

                        res = await db.execute(stmt)

                        activity: Activity = res.scalars().first()

                        if activity is None:
                            await asyncio.sleep(0.3)
                            continue

                        if activity.document_type == "printedPaper" or len(activity.text) < 50:
                            # set to finish
                            latch = ActivityLatch(
                                activity_id=activity.id, hasharr_instance_id=hasharr_id, latch="FINISHED"
                            )
                            db.add(latch)
                            await db.commit()
                            continue

                        latch = ActivityLatch(activity_id=activity.id, hasharr_instance_id=hasharr_id)
                        db.add(latch)
                        await db.commit()

                        event_type = {"event": "analyseEvent", "data": {"id": activity.id, "speech": activity.text}}
                        await dispatch_event(routes)(event_type, self.state)

                        latch = ActivityLatch(activity_id=activity.id, hasharr_instance_id=hasharr_id, latch="FINISHED")
                        db.add(latch)
                        await db.commit()

                    except Exception as e:
                        if isinstance(e, _KadiCloseException):
                            break
                        if "on_error" in lifecycles:
                            await lifecycles["on_error"](e)
                        else:
                            # print stacktrace
                            traceback.print_exc()
                            LOGGER.error(f"Error processing message: {e}")
                    finally:
                        if "on_close" in lifecycles:
                            await lifecycles["on_close"]()


def close():
    raise _KadiCloseException


class _KadiCloseException(Exception):
    pass
