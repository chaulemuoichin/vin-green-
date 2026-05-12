from __future__ import annotations

import json
import time
from dataclasses import asdict, dataclass
from datetime import datetime, timezone

from .config import Settings, get_settings
from .logging_setup import get_logger

logger = get_logger(__name__)


@dataclass(frozen=True)
class SourceConfig:
    name: str
    priority: int
    cadence_minutes: int
    timeout_seconds: int
    freshness_minutes: int
    quality_score: float
    quality_flag: str


SOURCE_REGISTRY: dict[str, SourceConfig] = {
    "open_meteo_weather": SourceConfig("open_meteo_weather", 10, 30, 12, 90, 0.88, "live_api"),
    "firms_viirs": SourceConfig("firms_viirs", 15, 180, 15, 360, 0.90, "satellite_nrt"),
    "open_meteo_air": SourceConfig("open_meteo_air", 20, 30, 18, 120, 0.82, "forecast_background"),
    "aqicn": SourceConfig("aqicn", 30, 30, 12, 120, 0.92, "live_api"),
    "openaq": SourceConfig("openaq", 40, 60, 15, 180, 0.86, "live_api"),
    "somo_crawler": SourceConfig("somo_crawler", 50, 30, 15, 180, 0.78, "public_crawl"),
    "cem_crawler": SourceConfig("cem_crawler", 60, 60, 15, 240, 0.72, "public_crawl"),
    "overpass_roads": SourceConfig("overpass_roads", 90, 43200, 45, 44640, 0.62, "static_proxy"),
}


def source_config(name: str) -> SourceConfig:
    return SOURCE_REGISTRY[name]


def registry_as_dict() -> list[dict]:
    return [
        asdict(item) for item in sorted(SOURCE_REGISTRY.values(), key=lambda item: item.priority)
    ]


def load_source_status(settings: Settings | None = None) -> dict:
    settings = settings or get_settings()
    path = settings.source_status_file
    if not path.exists():
        return {}
    try:
        with path.open("r", encoding="utf-8") as handle:
            return json.load(handle)
    except (OSError, json.JSONDecodeError) as exc:
        logger.warning("source_status file unreadable: {exc}", exc=exc)
        return {}


def save_source_status(status: dict, settings: Settings | None = None) -> None:
    settings = settings or get_settings()
    path = settings.source_status_file
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", encoding="utf-8") as handle:
        json.dump(status, handle, ensure_ascii=False, indent=2)


def should_fetch_source(
    source_name: str, settings: Settings | None = None, now: float | None = None
) -> bool:
    settings = settings or get_settings()
    config = source_config(source_name)
    status = load_source_status(settings).get(source_name, {})
    last_success = float(status.get("last_success_epoch") or 0)
    now_epoch = now if now is not None else time.time()
    return now_epoch - last_success >= config.cadence_minutes * 60


def mark_source_status(
    source_name: str,
    ok: bool,
    record_count: int = 0,
    message: str = "",
    settings: Settings | None = None,
) -> None:
    settings = settings or get_settings()
    status = load_source_status(settings)
    now_epoch = time.time()
    previous = status.get(source_name, {})
    # Start from the previous record so circuit-breaker fields
    # (consecutive_failures, circuit_open_until) survive across mark calls.
    item = dict(previous)
    item.update(
        {
            "last_attempt_epoch": now_epoch,
            "last_attempt_at": datetime.fromtimestamp(now_epoch, timezone.utc).isoformat(),
            "ok": bool(ok),
            "record_count": int(record_count),
            "message": message[:300],
        }
    )
    if ok:
        item["last_success_epoch"] = now_epoch
        item["last_success_at"] = item["last_attempt_at"]
    # else: keep last_success_* from previous record (already in item via dict copy)
    status[source_name] = item
    save_source_status(status, settings)
