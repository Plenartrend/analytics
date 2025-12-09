import gzip
import os
import shutil
import sys
from datetime import datetime
from logging import Handler, StreamHandler
from logging.handlers import RotatingFileHandler
from typing import Optional

from pydantic import TypeAdapter

from ..config.settings import settings
from .utils import MyJSONFormatter, SimpleFormatter


class GzippingRotatingFileHandler(RotatingFileHandler):
    def __init__(
        self,
        filename: str,
        mode: str = "a",
        max_bytes: int = 0,
        backup_count: int = 0,
        encoding: Optional[str] = None,
        delay: bool = False,
    ):
        self.backup_index = 0
        super().__init__(filename, mode, max_bytes, backup_count, encoding, delay)

    def doRollover(self):
        if self.stream:
            self.stream.close()
            self.stream = None

        should_compress = TypeAdapter(bool).validate_python(settings.LOGGER_FILE_COMPRESSION)
        self.backup_index += 1

        base_name, ext = os.path.splitext(self.baseFilename)
        rotated_filename = f"{base_name}_{self.backup_index}{ext}"

        if should_compress:
            rotated_filename += ".gz"
            with open(self.baseFilename, "rb") as source_file, gzip.open(rotated_filename, "wb") as gzipped_file:
                shutil.copyfileobj(source_file, gzipped_file)
            os.remove(self.baseFilename)
        else:
            self.rotate(self.baseFilename, rotated_filename)

        if not self.delay:
            self.stream = self._open()


def get_stdout_handler() -> Optional[Handler]:
    if not TypeAdapter(bool).validate_python(settings.LOGGER_STD_OUT_ENABLE_LOGGING):
        return None

    stdout_handler = StreamHandler(stream=sys.stdout)
    stdout_handler.setFormatter(SimpleFormatter())
    stdout_handler.setLevel(int(settings.LOGGER_STD_OUT_LOG_LEVEL))

    return stdout_handler


def get_file_handler() -> Optional[Handler]:
    if not TypeAdapter(bool).validate_python(settings.LOGGER_FILE_ENABLE_LOGGING):
        return None

    log_dir = str(settings.LOGGER_FILE_LOG_PATH)
    os.makedirs(log_dir, exist_ok=True)

    log_filename = os.path.join(log_dir, f"{datetime.today():%Y%m%d}_PID_{os.getpid()}.jsonl")

    file_handler = GzippingRotatingFileHandler(
        filename=log_filename,
        max_bytes=int(settings.LOGGER_FILE_BYTE_SIZE),
        backup_count=(2**16 - 1),
    )
    file_handler.setFormatter(MyJSONFormatter())
    file_handler.setLevel(int(settings.LOGGER_FILE_LOG_LEVEL))

    return file_handler
