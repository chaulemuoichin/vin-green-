"""Backtest math + archive loading."""

from __future__ import annotations

import json
import math
from datetime import datetime, timedelta, timezone
from pathlib import Path

from hanoi_air.config import Settings
from hanoi_air.validation import (
    backtest,
    compute_metrics,
    load_historical_readings,
    load_latest_backtest,
    save_backtest,
)


def test_compute_metrics_matches_hand_calculation() -> None:
    actual = [10.0, 20.0, 30.0, 40.0]
    predicted = [12.0, 18.0, 33.0, 38.0]
    # errors = [+2, -2, +3, -2]
    metrics = compute_metrics(actual, predicted)
    assert metrics["n"] == 4
    # RMSE = sqrt((4+4+9+4)/4) ≈ 2.291
    assert math.isclose(metrics["rmse"], 2.29, abs_tol=0.05)
    assert math.isclose(metrics["mae"], 2.25, abs_tol=0.05)
    assert math.isclose(metrics["mbe"], 0.25, abs_tol=0.05)
    # R² is high because the prediction tracks the trend
    assert metrics["r2"] > 0.95


def test_compute_metrics_handles_perfect_prediction() -> None:
    values = [5.0, 10.0, 15.0, 20.0]
    metrics = compute_metrics(values, values)
    assert metrics["rmse"] == 0.0
    assert metrics["mae"] == 0.0
    assert metrics["mbe"] == 0.0
    assert metrics["r2"] == 1.0


def test_compute_metrics_empty_inputs_return_nan() -> None:
    metrics = compute_metrics([], [])
    assert metrics["n"] == 0
    assert math.isnan(metrics["rmse"])


def _make_settings(tmp_path: Path) -> Settings:
    (tmp_path / "data" / "processed").mkdir(parents=True, exist_ok=True)
    (tmp_path / "data" / "sample").mkdir(parents=True, exist_ok=True)
    settings = Settings()
    return settings.model_copy(update={
        "project_root": tmp_path,
        "data_dir": tmp_path / "data",
        "sample_dir": tmp_path / "data" / "sample",
        "raw_dir": tmp_path / "data" / "raw",
        "processed_dir": tmp_path / "data" / "processed",
        "cache_file": tmp_path / ".cache" / "forecast_cache.json",
        "source_status_file": tmp_path / ".cache" / "source_status.json",
    })


def test_load_historical_readings_reads_jsonl(tmp_path: Path) -> None:
    settings = _make_settings(tmp_path)
    today = datetime.now(timezone.utc).strftime("%Y-%m-%d")
    path = settings.processed_dir / f"readings_{today}.jsonl"
    rows = [
        {
            "timestamp": datetime.now(timezone.utc).isoformat(),
            "source": "OpenAQ", "station_id": "s1", "station_name": "Test",
            "lat": 21.03, "lon": 105.83, "district": "Hoàn Kiếm",
            "pollutant": "pm25", "concentration": 42.5, "aqi": 117,
            "quality_flag": "live_api",
        },
        {
            "timestamp": datetime.now(timezone.utc).isoformat(),
            "source": "OpenAQ", "station_id": "s2", "station_name": "Other",
            "lat": 21.04, "lon": 105.79, "district": "Cầu Giấy",
            "pollutant": "no2", "concentration": 80.0, "aqi": 90,
            "quality_flag": "live_api",
        },
    ]
    with path.open("w", encoding="utf-8") as h:
        for row in rows:
            h.write(json.dumps(row, ensure_ascii=False) + "\n")

    pm25_only = load_historical_readings(settings=settings, days=2)
    assert len(pm25_only) == 1
    assert pm25_only[0].district == "Hoàn Kiếm"
    assert pm25_only[0].pollutant == "pm25"


def test_load_historical_readings_filters_by_age(tmp_path: Path) -> None:
    settings = _make_settings(tmp_path)
    old_day = (datetime.now(timezone.utc) - timedelta(days=10)).strftime("%Y-%m-%d")
    path = settings.processed_dir / f"readings_{old_day}.jsonl"
    path.write_text(
        json.dumps({
            "timestamp": (datetime.now(timezone.utc) - timedelta(days=10)).isoformat(),
            "source": "OpenAQ", "station_id": "s1", "station_name": "Test",
            "lat": 21.03, "lon": 105.83, "district": "Hoàn Kiếm",
            "pollutant": "pm25", "concentration": 42.5, "aqi": 117,
        }) + "\n",
        encoding="utf-8",
    )
    rows = load_historical_readings(settings=settings, days=3)
    assert rows == []


def test_backtest_with_no_archive_returns_status(tmp_path: Path) -> None:
    settings = _make_settings(tmp_path)
    result = backtest(settings=settings, days=7)
    assert result["status"] == "no_data"
    assert result["per_district"] == []


def test_save_and_load_backtest_round_trip(tmp_path: Path) -> None:
    settings = _make_settings(tmp_path)
    payload = {
        "status": "ok", "model": "heuristic", "days": 7,
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "overall": {"forecast": {"rmse": 8.4, "mae": 6.1, "r2": 0.91, "mbe": -0.2, "n": 24}},
        "per_district": [],
    }
    path = save_backtest(payload, settings=settings)
    assert path.exists()
    loaded = load_latest_backtest(settings=settings)
    assert loaded is not None
    assert loaded["overall"]["forecast"]["rmse"] == 8.4
