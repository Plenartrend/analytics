import logging
import logging.config
import logging.handlers
import queue

from ..config.settings import settings
from .handler import (
    get_file_handler,
    get_stdout_handler,
)


def setup_logging():
    que = queue.Queue(-1)
    queue_handler = logging.handlers.QueueHandler(que)

    root_logger = logging.getLogger()
    root_logger.setLevel(int(settings.LOGGER_DEFAULT_LOG_LEVEL))

    hdlrs = [hdlr for hdlr in [get_stdout_handler(), get_file_handler()] if hdlr is not None]
    listener = logging.handlers.QueueListener(que, *hdlrs, respect_handler_level=True)
    listener.start()

    root_logger.addHandler(queue_handler)

    # Configure third-party libraries
    logging.getLogger("httpx").disabled = settings.LOGGER_HTTP_ENABLE_LOGGING
    logging.getLogger("httpx").setLevel(settings.LOGGER_HTTP_LOG_LEVEL)
