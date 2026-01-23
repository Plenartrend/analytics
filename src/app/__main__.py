import asyncio

from .main import main
from .utils.logger import setup_logging

setup_logging()
asyncio.run(main())
