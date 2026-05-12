"""Forecast accuracy validation against archived station readings.

The pipeline persists processed station readings under
``data/processed/readings_YYYY-MM-DD.jsonl`` via
:func:`hanoi_air.archive.append_processed_readings`. This module reads
those archives, pairs them with the *current* forecast bundle's PM2.5
predictions per district-hour, and computes RMSE / MAE / R².

Limitations (documented honestly in the dashboard):
    - The pipeline does not yet archive forecast bundles, so the backtest
      compares observed readings against the latest in-memory forecast,
      not an as-of-that-hour forecast. A persistence baseline is included
      so the table has a comparison point even before the bundle archive
      ships.
    - If no archive exists yet, ``backtest()`` returns ``status="no_data"``
      so the UI can render a placeholder rather than a crash.
"""

from __future__ import annotations

import json
import math
import statistics
from collections.abc import Iterable
from dataclasses import dataclass
from datetime import datetime, timedelta, timezone
from pathlib import Path
from typing import Any

from .config import Settings, get_settings
from .geography import load_districts
from .logging_setup import get_logger
from .schemas import AirReading

logger = get_logger(__name__)


def compute_metrics(actual: Iterable[float], predicted: Iterable[float]) -> dict[str, float]:
    """Return RMSE, MAE, R², MBE, n for paired actual/predicted PM2.5."""
    a = [float(v) for v in actual]
    p = [float(v) for v in predicted]
    n = min(len(a), len(p))
    if n == 0:
        return {"rmse": float("nan"), "mae": float("nan"), "r2": float("nan"),
                "mbe": float("nan"), "n": 0}
    a, p = a[:n], p[:n]
    errors = [pi - ai for ai, pi in zip(a, p, strict=True)]
    abs_errors = [abs(e) for e in errors]
    mse = sum(e * e for e in errors) / n
    rmse = math.sqrt(mse)
    mae = sum(abs_errors) / n
    mbe = sum(errors) / n
    mean_a = sum(a) / n
    ss_res = sum((ai - pi) ** 2 for ai, pi in zip(a, p, strict=True))
    ss_tot = sum((ai - mean_a) ** 2 for ai in a)
    r2 = 1.0 - ss_res / ss_tot if ss_tot > 0 else float("nan")
    return {
        "rmse": round(rmse, 2),
        "mae": round(mae, 2),
        "r2": round(r2, 3),
        "mbe": round(mbe, 2),
        "n": n,
    }


@dataclass(frozen=True)
class _PairedSample:
    district_id: str
    actual_pm25: float
    predicted_pm25: float
    persistence_pm25: float
    timestamp: datetime


def load_historical_readings(
    settings: Settings | None = None,
    days: int = 7,
    now: datetime | None = None,
    pollutant: str = "pm25",
) -> list[AirReading]:
    """Read processed JSONL readings for the last ``days`` days."""
    settings = settings or get_settings()
    now = now or datetime.now(timezone.utc)
    cutoff = now - timedelta(days=days)
    rows: list[AirReading] = []
    for day_offset in range(days + 1):
        day = (now - timedelta(days=day_offset)).strftime("%Y-%m-%d")
        path = settings.processed_dir / f"readings_{day}.jsonl"
        if not path.exists():
            continue
        with path.open("r", encoding="utf-8") as handle:
            for line in handle:
                if not line.strip():
                    continue
                try:
                    row = json.loads(line)
                    if row.get("pollutant") != pollutant:
                        continue
                    timestamp = datetime.fromisoformat(row["timestamp"].replace("Z", "+00:00"))
                    if timestamp < cutoff:
                        continue
                    rows.append(
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
                            quality_flag=row.get("quality_flag") or "archive",
                        )
                    )
                except (KeyError, ValueError, TypeError) as exc:
                    logger.debug("backtest reading skipped: {exc}", exc=exc)
                    continue
    return rows


def _pair_samples(
    readings: list[AirReading],
    bundle: dict,
    settings: Settings | None = None,
) -> list[_PairedSample]:
    """Pair each reading with the bundle's T+0 forecast for its district."""
    settings = settings or get_settings()
    districts = load_districts(settings.sample_dir / "districts.csv")
    name_to_id = {d.name: d.district_id for d in districts}

    t0_by_district: dict[str, float] = {}
    for row in bundle.get("forecasts", []):
        if int(row.get("hour_offset", -1)) == 0:
            t0_by_district[row["district_id"]] = float(row["pm25"])

    # Per-district persistence baseline = the reading from ~24h before.
    by_district: dict[str, list[AirReading]] = {}
    for r in readings:
        if r.pollutant != "pm25":
            continue
        district_id = name_to_id.get(r.district)
        if not district_id:
            continue
        by_district.setdefault(district_id, []).append(r)

    paired: list[_PairedSample] = []
    for district_id, rows in by_district.items():
        predicted = t0_by_district.get(district_id)
        if predicted is None:
            continue
        rows.sort(key=lambda r: r.timestamp)
        median_pm25 = statistics.median(r.concentration for r in rows)
        latest = rows[-1]
        # Persistence = the median of the prior window (more robust than a
        # single value when station cadence is irregular).
        paired.append(
            _PairedSample(
                district_id=district_id,
                actual_pm25=float(latest.concentration),
                predicted_pm25=float(predicted),
                persistence_pm25=float(median_pm25),
                timestamp=latest.timestamp,
            )
        )
    return paired


def backtest(
    settings: Settings | None = None,
    days: int = 7,
    model: str = "heuristic",
    bundle: dict | None = None,
) -> dict[str, Any]:
    """Compare forecast PM2.5 against archived station observations.

    Returns a dict with ``overall`` metrics and ``per_district`` rows
    suitable for direct rendering by the dashboard or CLI.
    """
    settings = settings or get_settings()
    readings = load_historical_readings(settings=settings, days=days)
    if not readings:
        return {
            "status": "no_data",
            "model": model,
            "days": days,
            "generated_at": datetime.now(timezone.utc).isoformat(),
            "note": (
                "No archived station readings found under data/processed/. "
                "Run the live ingestion path for at least one cadence cycle, "
                "then re-run the backtest."
            ),
            "overall": {},
            "per_district": [],
        }

    if bundle is None:
        # Local import to avoid circular dependency (forecast → validation
        # is fine because validation is only called from outside the loop).
        from .forecast import build_cached_forecast

        bundle = build_cached_forecast(settings=settings, use_live=False)

    paired = _pair_samples(readings, bundle, settings=settings)
    if not paired:
        return {
            "status": "no_overlap",
            "model": model,
            "days": days,
            "generated_at": datetime.now(timezone.utc).isoformat(),
            "note": "Archive present but no district overlap with current bundle.",
            "overall": {},
            "per_district": [],
        }

    per_district: list[dict[str, Any]] = []
    for sample in paired:
        per_district.append({
            "district_id": sample.district_id,
            "actual_pm25": round(sample.actual_pm25, 1),
            "forecast_pm25": round(sample.predicted_pm25, 1),
            "persistence_pm25": round(sample.persistence_pm25, 1),
            "abs_error": round(abs(sample.predicted_pm25 - sample.actual_pm25), 1),
            "persistence_abs_error": round(
                abs(sample.persistence_pm25 - sample.actual_pm25), 1
            ),
        })

    overall_forecast = compute_metrics(
        [s.actual_pm25 for s in paired],
        [s.predicted_pm25 for s in paired],
    )
    overall_persistence = compute_metrics(
        [s.actual_pm25 for s in paired],
        [s.persistence_pm25 for s in paired],
    )
    improvement = (
        round(overall_persistence["rmse"] - overall_forecast["rmse"], 2)
        if overall_persistence["rmse"] and overall_forecast["rmse"]
        else None
    )
    return {
        "status": "ok",
        "model": model,
        "days": days,
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "overall": {
            "forecast": overall_forecast,
            "persistence_baseline": overall_persistence,
            "rmse_improvement_vs_persistence": improvement,
        },
        "per_district": per_district,
    }


def save_backtest(result: dict[str, Any], settings: Settings | None = None) -> Path:
    settings = settings or get_settings()
    settings.processed_dir.mkdir(parents=True, exist_ok=True)
    stamp = datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ")
    path = settings.processed_dir / f"backtest_{stamp}.json"
    with path.open("w", encoding="utf-8") as handle:
        json.dump(result, handle, ensure_ascii=False, indent=2)
    return path


def load_latest_backtest(settings: Settings | None = None) -> dict[str, Any] | None:
    settings = settings or get_settings()
    if not settings.processed_dir.exists():
        return None
    matches = sorted(settings.processed_dir.glob("backtest_*.json"))
    if not matches:
        return None
    try:
        with matches[-1].open("r", encoding="utf-8") as handle:
            return json.load(handle)
    except (OSError, json.JSONDecodeError) as exc:
        logger.warning("failed to load backtest snapshot: {exc}", exc=exc)
        return None
