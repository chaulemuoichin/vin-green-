"""Structured logging configuration for the Hanoi Air pipeline.

Imports loguru lazily so the package still works on a bare interpreter that has
not installed it yet (e.g. CI building documentation). Call ``configure_logging``
once at the entrypoint of each process (api, worker, dashboard, scripts).
"""

from __future__ import annotations

import os
import sys
from typing import Literal

LogLevel = Literal["TRACE", "DEBUG", "INFO", "SUCCESS", "WARNING", "ERROR", "CRITICAL"]

_configured = False


def configure_logging(
    level: LogLevel | str = "INFO",
    *,
    json_output: bool | None = None,
    service: str = "hanoi-air",
) -> None:
    """Initialise loguru with a sensible default sink.

    json_output=True emits one JSON object per line (good for production log
    shippers). Defaults to True when ``HANOI_AIR_LOG_JSON`` is set, else
    falls back to human-readable colored output for local development.
    """
    global _configured
    if _configured:
        return

    try:
        from loguru import logger
    except ImportError:
        # loguru not installed yet; fall back to stdlib logging so callers do
        # not crash. Production deploys must install requirements.
        import logging

        logging.basicConfig(level=str(level).upper())
        _configured = True
        return

    logger.remove()

    if json_output is None:
        json_output = os.getenv("HANOI_AIR_LOG_JSON", "").lower() in {"1", "true", "yes"}

    fmt_human = (
        "<green>{time:YYYY-MM-DD HH:mm:ss.SSS}</green> "
        "<level>{level: <8}</level> "
        "<cyan>{name}</cyan>:<cyan>{function}</cyan>:<cyan>{line}</cyan> - "
        "<level>{message}</level>"
    )

    logger.add(
        sys.stderr,
        level=str(level).upper(),
        format=fmt_human if not json_output else "{message}",
        serialize=json_output,
        backtrace=True,
        diagnose=False,  # do not leak local variables in production
        enqueue=False,
    )

    # Bind static context for every log line
    logger.configure(extra={"service": service})

    _configured = True


def get_logger(name: str | None = None):
    """Return a loguru logger bound to the given module name.

    Falls back to stdlib ``logging.Logger`` if loguru is unavailable so callers
    can use the same call sites in any environment.
    """
    try:
        from loguru import logger

        if name:
            return logger.bind(module=name)
        return logger
    except ImportError:
        import logging

        return logging.getLogger(name or "hanoi_air")
