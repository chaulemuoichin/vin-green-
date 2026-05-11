from __future__ import annotations

import json
import time
from collections.abc import Iterable
from datetime import datetime, timedelta, timezone
from pathlib import Path

from .config import Settings, get_settings
from .logging_setup import get_logger
from .schemas import AirQualityForecast, AirReading, WeatherHour

logger = get_logger(__name__)


def archive_raw_payload(
    source_name: str,
    payload: object,
    extension: str = "json",
    settings: Settings | None = None,
    timestamp: datetime | None = None,
) -> Path:
    settings = settings or get_settings()
    timestamp = timestamp or datetime.now(timezone.utc)
    day_dir = settings.raw_dir / source_name / timestamp.strftime("%Y-%m-%d")
    day_dir.mkdir(parents=True, exist_ok=True)
    path = (
        day_dir / f"{timestamp.strftime('%H%M%S')}_{int(time.time() * 1000) % 100000}.{extension}"
    )
    if extension == "json":
        with path.open("w", encoding="utf-8") as handle:
            json.dump(payload, handle, ensure_ascii=False, indent=2)
    else:
        with path.open("w", encoding="utf-8") as handle:
            handle.write(str(payload))
    return path


def append_processed_readings(
    readings: Iterable[AirReading],
    settings: Settings | None = None,
) -> None:
    settings = settings or get_settings()
    items = list(readings)
    if not items:
        return
    settings.processed_dir.mkdir(parents=True, exist_ok=True)
    path = (
        settings.processed_dir / f"readings_{datetime.now(timezone.utc).strftime('%Y-%m-%d')}.jsonl"
    )
    with path.open("a", encoding="utf-8") as handle:
        for item in items:
            handle.write(json.dumps(item.to_dict(), ensure_ascii=False) + "\n")


def load_recent_processed_readings(
    source_name: str,
    max_age_minutes: int,
    settings: Settings | None = None,
    now: datetime | None = None,
) -> list[AirReading]:
    settings = settings or get_settings()
    now = now or datetime.now(timezone.utc)
    cutoff = now - timedelta(minutes=max_age_minutes)
    readings: list[AirReading] = []
    for path in _recent_jsonl_files(settings.processed_dir, "readings", now):
        with path.open("r", encoding="utf-8") as handle:
            for line in handle:
                if not line.strip():
                    continue
                try:
                    row = json.loads(line)
                    if row.get("source_key") != source_name and row.get("source") != source_name:
                        continue
                    timestamp = _parse_datetime(row["timestamp"])
                    if timestamp < cutoff:
                        continue
                    readings.append(
                        AirReading(
                            timestamp=timestamp,
                            source=row["source"],
                            station_id=row["station_id"],
                            station_name=row["station_name"],
                            lat=float(row["lat"]),
                            lon=float(row["lon"]),
                            district=row["district"],
                            pollutant=row["pollutant"],
                            concentration=float(row["concentration"]),
                            aqi=float(row["aqi"]) if row.get("aqi") is not None else None,
                            quality_flag=row.get("quality_flag") or "live_api",
                        )
                    )
                except (KeyError, ValueError, TypeError) as exc:
                    logger.debug("processed reading row skipped: {exc}", exc=exc)
                    continue
    return readings


def _parse_datetime(value: str) -> datetime:
    return datetime.fromisoformat(value.replace("Z", "+00:00"))


def save_weather_forecast(
    hours: Iterable[WeatherHour],
    source_name: str,
    settings: Settings | None = None,
) -> None:
    settings = settings or get_settings()
    items = list(hours)
    if not items:
        return
    settings.processed_dir.mkdir(parents=True, exist_ok=True)
    path = (
        settings.processed_dir / f"weather_{datetime.now(timezone.utc).strftime('%Y-%m-%d')}.jsonl"
    )
    with path.open("a", encoding="utf-8") as handle:
        for item in items:
            row = item.to_dict()
            row["source_key"] = source_name
            handle.write(json.dumps(row, ensure_ascii=False) + "\n")


def save_air_quality_forecast(
    rows: Iterable[AirQualityForecast],
    source_name: str,
    settings: Settings | None = None,
) -> None:
    settings = settings or get_settings()
    items = list(rows)
    if not items:
        return
    settings.processed_dir.mkdir(parents=True, exist_ok=True)
    path = (
        settings.processed_dir
        / f"air_forecast_{datetime.now(timezone.utc).strftime('%Y-%m-%d')}.jsonl"
    )
    with path.open("a", encoding="utf-8") as handle:
        for item in items:
            row = item.to_dict()
            row["source_key"] = source_name
            handle.write(json.dumps(row, ensure_ascii=False) + "\n")


def _recent_jsonl_files(directory: Path, prefix: str, now: datetime) -> list[Path]:
    if not directory.exists():
        return []
    dates = {now.strftime("%Y-%m-%d"), (now - timedelta(days=1)).strftime("%Y-%m-%d")}
    return [
        directory / f"{prefix}_{date}.jsonl"
        for date in dates
        if (directory / f"{prefix}_{date}.jsonl").exists()
    ]
