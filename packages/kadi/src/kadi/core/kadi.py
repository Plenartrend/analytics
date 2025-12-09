import json
import logging
from contextlib import contextmanager
from typing import Any, Callable

from confluent_kafka import Consumer

from ..config.config import KadiConfig
from ..dclasses import Event

LOGGER = logging.getLogger("kadi")

def dispatch_event(routes: dict[str: Callable]):
    async def wrapper(message: Any):
        to_object = Event.from_dict(json.loads(message))
        LOGGER.log(logging.INFO, f"Request to {to_object.event}")
        await routes[to_object.event](to_object.data)

    return wrapper


def collect_routes(config: KadiConfig):
    routes = {}
    for router in config.routes:
        for key in router._store.keys():
            routes[key] = router._store[key]
    return routes


def collect_lifecycle(config: KadiConfig):
    lifecycle = {}
    for life in config.lifecycle:
        for key in life._store.keys():
            lifecycle[key] = life._store[key]
    return lifecycle


@contextmanager
def build_consumer(config: KadiConfig):
    c = Consumer(config.settings)
    c.subscribe(config.topics)
    try:
        yield c
    finally:
        c.close()


class Kadi:
    def __init__(self, config: KadiConfig):
        self.config = config

    async def run(self):
        routes = collect_routes(self.config)
        lifecycles = collect_lifecycle(self.config)

        with build_consumer(self.config) as consumer:
            if "on_open" in lifecycles:
                await lifecycles["on_open"]()
            while True:
                try:
                    msg = consumer.poll(0.2)
                    if msg is None:
                        continue
                    if msg.error():
                        raise Exception(msg.error())
                    await dispatch_event(routes)(msg.value())
                except Exception as e:
                    if isinstance(e, _KadiCloseException):
                        break
                    if "on_error" in lifecycles:
                        await lifecycles["on_error"](e)
                    else:
                        LOGGER.error(f"Error processing message: {e}")
                finally:
                    if "on_close" in lifecycles:
                        await lifecycles["on_close"]()

def close():
    raise _KadiCloseException


class _KadiCloseException(Exception):
    pass