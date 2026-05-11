"""Forecast / source cache with atomic file writes + multi-process locking.

Two backends are supported transparently:

* **Redis** — selected when ``settings.redis_url`` is set. SETEX is atomic.
* **File** — local JSON at ``settings.cache_file``. Writes go through a
  per-file ``filelock`` and ``tempfile + os.replace`` for atomicity, so two
  workers cannot tear or lose each other's writes.

Read paths fall back to ``None`` and log a warning if the file is corrupted —
they never raise. Write paths log and re-raise on filesystem errors so the
caller can decide whether to retry.
"""

from __future__ import annotations

import json
import os
import tempfile
import time
from pathlib import Path
from typing import Any

from filelock import FileLock, Timeout

from .config import Settings, get_settings
from .logging_setup import get_logger

logger = get_logger(__name__)

# Lock files live next to the cache. We use a small timeout so callers fail
# fast rather than block the dashboard render thread.
_LOCK_TIMEOUT_SECONDS = 5.0


def _lock_for(path: Path) -> FileLock:
    return FileLock(str(path) + ".lock", timeout=_LOCK_TIMEOUT_SECONDS)


def load_cache(key: str = "forecast", settings: Settings | None = None) -> dict | None:
    settings = settings or get_settings()

    redis_payload = _redis_get(key, settings)
    if redis_payload:
        return redis_payload

    path = settings.cache_file
    if not path.exists():
        return None
    try:
        with path.open("r", encoding="utf-8") as handle:
            payload = json.load(handle)
        item = payload.get(key)
        if not item:
            return None
        if item.get("expires_at", 0) < time.time():
            return None
        return item.get("value")
    except (OSError, json.JSONDecodeError) as exc:
        logger.warning("cache load failed for key={key}: {exc}", key=key, exc=exc)
        return None


def save_cache(
    value: dict,
    key: str = "forecast",
    settings: Settings | None = None,
    ttl_seconds: int | None = None,
) -> None:
    settings = settings or get_settings()
    ttl = ttl_seconds or settings.cache_ttl_seconds

    if _redis_set(key, value, settings, ttl):
        return

    path = settings.cache_file
    path.parent.mkdir(parents=True, exist_ok=True)

    try:
        with _lock_for(path):
            # Read-modify-write under the lock so we never lose a sibling key.
            payload: dict[str, Any] = {}
            if path.exists():
                try:
                    with path.open("r", encoding="utf-8") as handle:
                        payload = json.load(handle)
                except (OSError, json.JSONDecodeError) as exc:
                    logger.warning("cache read corrupted, resetting: {exc}", exc=exc)
                    payload = {}

            payload[key] = {"expires_at": time.time() + ttl, "value": value}
            _atomic_write_json(path, payload)
    except Timeout:
        logger.error(
            "cache write timed out waiting for lock on {path}; key={key} skipped",
            path=path,
            key=key,
        )


def _atomic_write_json(path: Path, payload: dict[str, Any]) -> None:
    """Write JSON atomically via tempfile + os.replace.

    os.replace is atomic on POSIX and on Windows when source/dest are on the
    same volume. We create the temp file in the same directory to guarantee
    that.
    """
    fd, tmp_name = tempfile.mkstemp(
        prefix=path.stem + ".",
        suffix=".tmp",
        dir=str(path.parent),
    )
    tmp_path = Path(tmp_name)
    try:
        with os.fdopen(fd, "w", encoding="utf-8") as handle:
            json.dump(payload, handle, ensure_ascii=False, indent=2)
            handle.flush()
            os.fsync(handle.fileno())
        os.replace(tmp_path, path)
    except Exception:
        # Best effort cleanup; don't mask the real error.
        try:
            if tmp_path.exists():
                tmp_path.unlink()
        except OSError:
            pass
        raise


def _redis_get(key: str, settings: Settings) -> dict | None:
    if not settings.redis_url:
        return None
    try:
        import redis  # type: ignore

        client = redis.from_url(settings.redis_url)
        raw = client.get(f"hanoi_air:{key}")
        return json.loads(raw) if raw else None
    except Exception as exc:
        logger.warning("redis cache GET failed for {key}: {exc}", key=key, exc=exc)
        return None


def _redis_set(key: str, value: dict, settings: Settings, ttl_seconds: int) -> bool:
    if not settings.redis_url:
        return False
    try:
        import redis  # type: ignore

        client = redis.from_url(settings.redis_url)
        client.setex(f"hanoi_air:{key}", ttl_seconds, json.dumps(value, ensure_ascii=False))
        return True
    except Exception as exc:
        logger.warning("redis cache SET failed for {key}: {exc}", key=key, exc=exc)
        return False
