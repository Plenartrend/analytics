import datetime as dt
import json
import logging

from typing_extensions import override

LOG_RECORD_BUILTIN_ATTRS = {
    "args",
    "asctime",
    "created",
    "exc_info",
    "exc_text",
    "filename",
    "funcName",
    "levelname",
    "levelno",
    "lineno",
    "module",
    "msecs",
    "message",
    "msg",
    "name",
    "pathname",
    "process",
    "processName",
    "relativeCreated",
    "stack_info",
    "thread",
    "threadName",
    "taskName",
}


class SimpleFormatter(logging.Formatter):
    grey = "\x1b[38;20m"
    blue = "\x1b[0;34m"
    green = "\x1b[0;32m"
    yellow = "\x1b[33;20m"
    red = "\x1b[31;20m"
    bold_red = "\x1b[31;1m"
    reset = "\x1b[0m"

    fmt = "[%(levelname)s|%(module)s|L%(lineno)d] %(asctime)s: %(message)s"
    datefmt = "%Y-%m-%dT%H:%M:%S%z"

    FORMATS = {
        logging.DEBUG: blue + fmt[: (fmt.find("]") + 1)] + reset + fmt[(fmt.find("]") + 1) :],
        logging.INFO: green + fmt[: (fmt.find("]") + 1)] + reset + fmt[(fmt.find("]") + 1) :],
        logging.WARNING: yellow + fmt[: (fmt.find("]") + 1)] + reset + fmt[(fmt.find("]") + 1) :],
        logging.ERROR: red + fmt[: (fmt.find("]") + 1)] + reset + fmt[(fmt.find("]") + 1) :],
        logging.CRITICAL: bold_red + fmt[: (fmt.find("]") + 1)] + reset + fmt[(fmt.find("]") + 1) :],
    }

    @override
    def format(self, record: logging.LogRecord) -> str:
        log_fmt = self.FORMATS.get(record.levelno)
        formatter = logging.Formatter(fmt=log_fmt, datefmt=self.datefmt)
        return formatter.format(record)


class MyJSONFormatter(logging.Formatter):
    def __init__(self):
        super().__init__()

        self.fmt_keys = {
            "level": "levelname",
            "message": "message",
            "timestamp": "timestamp",
            "logger": "name",
            "module": "module",
            "function": "funcName",
            "line": "lineno",
            "thread_name": "threadName",
        }

    @override
    def format(self, record: logging.LogRecord) -> str:
        message = self._prepare_log_dict(record)
        return json.dumps(message, default=str)

    def _prepare_log_dict(self, record: logging.LogRecord):
        always_fields = {
            "message": record.getMessage(),
            "timestamp": dt.datetime.fromtimestamp(record.created, tz=dt.timezone.utc).isoformat(),
        }
        if record.exc_info is not None:
            always_fields["exc_info"] = self.formatException(record.exc_info)

        if record.stack_info is not None:
            always_fields["stack_info"] = self.formatStack(record.stack_info)

        message = {
            key: (msg_val if (msg_val := always_fields.pop(val, None)) is not None else getattr(record, val))
            for key, val in self.fmt_keys.items()
        }
        message.update(always_fields)

        for key, val in record.__dict__.items():
            if key not in LOG_RECORD_BUILTIN_ATTRS:
                message[key] = val

        return message
