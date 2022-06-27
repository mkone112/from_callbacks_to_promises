import sys
from functools import lru_cache

from loguru import logger

logger.remove()


@lru_cache(None)
def get_console(format):
    logger.add(
        sys.stdout,
        level="INFO",
        filter=lambda rec: rec['extra']['format'] == format,
        format=format,
    )
    return logger.bind(format=format).info
