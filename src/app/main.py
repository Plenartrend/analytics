import asyncio
from logging import Logger

from annotations.logger import inject_logger
from kadi import Kadi, KadiConfig, Lifecycle

from app.routes.analyse_route import router
from app.utils.config.settings import settings
from app.utils.logger import setup_logging

lifecycle = Lifecycle()


@lifecycle.on_open()
@inject_logger
async def on_open(logger: Logger = None):
    logger.info("Application ready to listen to incoming messages")


@inject_logger
async def main(logger: Logger = None):
    logger.info("Application starting...")

    await Kadi(
        config=KadiConfig(
            settings={
                "bootstrap.servers": settings.KAFKA_BROKER,
                "group.id": "test-group",
                "auto.offset.reset": "earliest",
            },
            topics=[settings.TOPIC],
            routes=[router],
            lifecycle=[lifecycle],
        )
    ).run()

    logger.info("Application finished")


if __name__ == "__main__":
    setup_logging()
    asyncio.run(main())
