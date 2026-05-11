"""Source-level resilience: circuit breaker on top of source_status tracking.

The HTTP layer (``hanoi_air.http``) already retries individual requests with
exponential backoff. This module adds a higher-level guard: when an entire
``fetch_*`` function fails N times in a row, we short-circuit subsequent calls
for a cooldown window so we stop wasting timeouts on a known-dead endpoint.

Usage::

    @guard_source("aqicn")
    def fetch_aqicn_readings(settings) -> list[AirReading]:
        ...

The decorator:

1. Reads ``source_status[name]`` from disk.
2. If ``circuit_open_until`` is in the future, logs and returns ``[]`` without
   calling the wrapped function.
3. Otherwise calls the function. On success, resets ``consecutive_failures``.
   On exception, increments ``consecutive_failures``; once it reaches
   ``threshold`` (default 3), opens the breaker for ``cooldown_minutes``
   (default 5).
"""

from __future__ import annotations

import time
from collections.abc import Callable
from functools import wraps
from typing import Any, TypeVar

from .config import Settings, get_settings
from .logging_setup import get_logger
from .sources import load_source_status, mark_source_status, save_source_status

logger = get_logger(__name__)

T = TypeVar("T")

DEFAULT_THRESHOLD = 3
DEFAULT_COOLDOWN_MINUTES = 5


def is_circuit_open(
    source_name: str,
    settings: Settings | None = None,
    *,
    now_epoch: float | None = None,
) -> bool:
    """Return True if the circuit breaker for ``source_name`` is currently open."""
    settings = settings or get_settings()
    status = load_source_status(settings).get(source_name) or {}
    open_until = float(status.get("circuit_open_until") or 0)
    now = now_epoch if now_epoch is not None else time.time()
    return open_until > now


def _record_failure(
    source_name: str,
    settings: Settings,
    threshold: int,
    cooldown_minutes: int,
    message: str,
) -> None:
    status = load_source_status(settings)
    item = status.get(source_name, {})
    consecutive = int(item.get("consecutive_failures") or 0) + 1
    item["consecutive_failures"] = consecutive
    if consecutive >= threshold:
        item["circuit_open_until"] = time.time() + cooldown_minutes * 60
        logger.warning(
            "circuit OPENED for {src} after {n} failures; cooldown {m} min — {msg}",
            src=source_name,
            n=consecutive,
            m=cooldown_minutes,
            msg=message[:120],
        )
    status[source_name] = item
    save_source_status(status, settings)


def _record_success(source_name: str, settings: Settings) -> None:
    status = load_source_status(settings)
    item = status.get(source_name, {})
    was_failing = int(item.get("consecutive_failures") or 0) > 0 or item.get("circuit_open_until")
    item["consecutive_failures"] = 0
    item["circuit_open_until"] = 0
    status[source_name] = item
    save_source_status(status, settings)
    if was_failing:
        logger.info("circuit CLOSED for {src} (success after failures)", src=source_name)


def guard_source(
    source_name: str,
    *,
    threshold: int = DEFAULT_THRESHOLD,
    cooldown_minutes: int = DEFAULT_COOLDOWN_MINUTES,
    fallback: Any = None,
) -> Callable[[Callable[..., T]], Callable[..., T]]:
    """Decorator that short-circuits a fetch function when its breaker is open.

    Args:
        source_name: must match a key in ``SOURCE_REGISTRY``.
        threshold: open the breaker after this many consecutive failures.
        cooldown_minutes: time to stay open before re-trying.
        fallback: value returned while the breaker is open and on uncaught
            exceptions (defaults to ``None``; ``fetch_*`` functions typically
            pass ``fallback=[]``).
    """

    def decorator(fn: Callable[..., T]) -> Callable[..., T]:
        @wraps(fn)
        def wrapper(*args: Any, **kwargs: Any) -> T:
            settings = kwargs.get("settings") or (args[0] if args else None) or get_settings()
            if not isinstance(settings, Settings):
                settings = get_settings()

            if is_circuit_open(source_name, settings):
                logger.info(
                    "skipping {src} fetch — circuit open",
                    src=source_name,
                )
                return fallback  # type: ignore[return-value]

            try:
                result = fn(*args, **kwargs)
            except Exception as exc:
                _record_failure(
                    source_name, settings, threshold, cooldown_minutes, message=str(exc)
                )
                mark_source_status(source_name, False, 0, str(exc), settings)
                logger.warning(
                    "{src} fetch raised: {exc}",
                    src=source_name,
                    exc=exc,
                )
                return fallback  # type: ignore[return-value]

            # Success: only reset the breaker; mark_source_status is called by the
            # fetcher itself with the actual record_count.
            _record_success(source_name, settings)
            return result

        return wrapper

    return decorator
