import asyncio
from logging import Logger

from hashrr import Hashrr, HashrrConfig
from podi import Lifecycle, Podi, PodiConfig

from .annotations.logger import inject_logger
from .repositories import hashrr_repository as hashrr_repo
from .routes.analyse_route import router
from .schema import schema
from .utils.config.settings import settings
from .utils.db import get_db

lifecycle = Lifecycle()


@lifecycle.on_open()
@inject_logger
async def on_open(logger: Logger = None):
    logger.info("Application ready to listen to incoming messages")


@inject_logger
async def _main(instance: int, logger: Logger = None):
    logger.info(f"Instance {instance} starting...")

    hashrr = Hashrr(
        config=HashrrConfig(
            register_callback=hashrr_repo.register_callback,
            send_heartbeat_callback=hashrr_repo.send_heartbeat_callback,
            unregister_callback=hashrr_repo.unregister_callback,
            get_my_node_callback=hashrr_repo.get_my_node_callback,
            get_all_nodes_callback=hashrr_repo.get_all_nodes_callback,
            get_all_running_nodes_callback=hashrr_repo.get_all_running_nodes_callback,
        )
    )

    await hashrr.cleanup()
    await hashrr.connect()

    await Podi(
        config=PodiConfig(
            settings=settings,
        ),
        routes=[router],
        lifecycle=[lifecycle],
        state=schema.State(db_session=get_db, distributed_key_function=hashrr.get_distributed_key),
    ).run()

    await hashrr.stop()

    logger.info("Application finished")


async def main():
    tasks = [asyncio.create_task(_main(i)) for i in range(1)]
    await asyncio.gather(*tasks)
