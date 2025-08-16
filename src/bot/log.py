"""Unified logger: prefers loguru, falls back to stdlib logging.

Usage:
    from .log import logger
"""

from __future__ import annotations

try:  # pragma: no cover
    from loguru import logger as logger  # type: ignore  # noqa: F401
except ImportError:  # pragma: no cover
    import logging

    class _StdLogger:
        def __init__(self) -> None:
            logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(message)s")
            self._logger = logging.getLogger("ibkr-bot")

        def debug(self, *args, **kwargs):
            return self._logger.debug(*args, **kwargs)

        def info(self, *args, **kwargs):
            return self._logger.info(*args, **kwargs)

        def warning(self, *args, **kwargs):
            return self._logger.warning(*args, **kwargs)

        def error(self, *args, **kwargs):
            return self._logger.error(*args, **kwargs)

        def exception(self, *args, **kwargs):
            return self._logger.exception(*args, **kwargs)

        def bind(self, **_kwargs):
            # Compatibility shim; returns self without structured binding
            return self

    logger = _StdLogger()
