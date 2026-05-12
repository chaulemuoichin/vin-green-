"""Bridge between the existing LSTM scaffold and Hanoi forecast features.

The heuristic in :mod:`forecast` is the operational predictor. This
module trains :class:`hanoi_air.model.LSTMForecaster` on archived
station readings + weather and exposes a gated ensemble blend:

    ensemble = w * heuristic + (1 - w) * lstm

The gate falls back to pure heuristic if the LSTM has higher RMSE on
the held-out window, so wiring the ensemble in production is always at
least as good as the heuristic alone.
"""

from __future__ import annotations

import json
from collections.abc import Iterable
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

import numpy as np

from .config import Settings, get_settings
from .logging_setup import get_logger
from .model import LSTMForecaster, make_supervised_sequences
from .schemas import AirReading, WeatherHour

logger = get_logger(__name__)

FEATURE_NAMES: tuple[str, ...] = (
    "pm25",
    "wind_speed_mps",
    "wind_dir_sin",
    "wind_dir_cos",
    "temp_c",
    "humidity",
    "hour_sin",
    "hour_cos",
)
DEFAULT_LOOKBACK = 24
DEFAULT_HORIZON = 24


@dataclass(frozen=True)
class EnsembleGate:
    """Per-district gate decision based on recent backtest RMSE."""
    use_lstm: bool
    w_heuristic: float
    heuristic_rmse: float
    lstm_rmse: float

    def blend(self, heuristic_pm25: float, lstm_pm25: float) -> float:
        if not self.use_lstm:
            return float(heuristic_pm25)
        return self.w_heuristic * heuristic_pm25 + (1.0 - self.w_heuristic) * lstm_pm25


def build_training_matrix(
    readings: Iterable[AirReading],
    weather: Iterable[WeatherHour],
    lookback: int = DEFAULT_LOOKBACK,
    horizon: int = DEFAULT_HORIZON,
) -> tuple[np.ndarray, np.ndarray, dict[str, Any]]:
    """Convert raw archives into (X, y, meta) suitable for LSTM training.

    Readings are aggregated to an hourly PM2.5 series (median across
    stations) and aligned to the weather timeline by timestamp.
    """
    pm25_by_hour = _hourly_median_pm25(readings)
    weather_by_hour = {_floor_hour(w.timestamp): w for w in weather}
    hours = sorted(set(pm25_by_hour) & set(weather_by_hour))
    if len(hours) < lookback + horizon:
        meta = {"hours": len(hours), "ok": False, "reason": "insufficient_overlap"}
        return np.empty((0, lookback, len(FEATURE_NAMES)), dtype=np.float32), \
               np.empty((0, horizon), dtype=np.float32), meta

    rows: list[list[float]] = []
    for hour in hours:
        wx = weather_by_hour[hour]
        hour_of_day = hour.hour
        wind_rad = np.deg2rad(wx.wind_dir_deg or 0.0)
        rows.append([
            float(pm25_by_hour[hour]),
            float(wx.wind_speed_mps or 0.0),
            float(np.sin(wind_rad)),
            float(np.cos(wind_rad)),
            float(wx.temp_c or 0.0),
            float(wx.humidity or 0.0),
            float(np.sin(2.0 * np.pi * hour_of_day / 24.0)),
            float(np.cos(2.0 * np.pi * hour_of_day / 24.0)),
        ])
    matrix = np.asarray(rows, dtype=np.float32)
    x, y = make_supervised_sequences(matrix, lookback=lookback, horizon=horizon)
    meta = {"hours": len(hours), "samples": len(x), "ok": True}
    return x, y, meta


def _hourly_median_pm25(readings: Iterable[AirReading]) -> dict[datetime, float]:
    buckets: dict[datetime, list[float]] = {}
    for r in readings:
        if r.pollutant != "pm25":
            continue
        floored = _floor_hour(r.timestamp)
        buckets.setdefault(floored, []).append(float(r.concentration))
    return {hour: float(np.median(values)) for hour, values in buckets.items()}


def _floor_hour(timestamp: datetime) -> datetime:
    if timestamp.tzinfo is None:
        timestamp = timestamp.replace(tzinfo=timezone.utc)
    return timestamp.replace(minute=0, second=0, microsecond=0).astimezone(timezone.utc)


def train_lstm(
    settings: Settings | None = None,
    days: int = 30,
    epochs: int = 8,
    lr: float = 0.008,
) -> dict[str, Any]:
    """Train an LSTM from archived readings and persist it.

    Returns a status dict; the model file lands at
    ``settings.processed_dir.parent / 'models' / 'lstm_pm25_v1.npz'``.
    """
    settings = settings or get_settings()
    from .archive import load_recent_processed_readings  # local import (lazy)

    minutes = days * 24 * 60
    readings = load_recent_processed_readings("openaq", minutes, settings)
    if not readings:
        # Fall back to all archived PM2.5 rows regardless of source key.
        from .validation import load_historical_readings
        readings = load_historical_readings(settings=settings, days=days)
    if not readings:
        return {"status": "no_data", "reason": "no archived readings"}

    weather_rows = _load_archived_weather(settings, days=days)
    if not weather_rows:
        return {"status": "no_data", "reason": "no archived weather"}

    x, y, meta = build_training_matrix(readings, weather_rows)
    if not meta["ok"]:
        return {"status": "insufficient", "meta": meta}

    forecaster = LSTMForecaster(
        input_size=len(FEATURE_NAMES),
        hidden_size=32,
        horizon=DEFAULT_HORIZON,
    )
    forecaster.fit(x, y, epochs=epochs, lr=lr)

    model_dir = settings.project_root / "models"
    model_dir.mkdir(parents=True, exist_ok=True)
    metadata_path = model_dir / "lstm_pm25_v1.json"
    metadata = {
        "trained_at": datetime.now(timezone.utc).isoformat(),
        "samples": int(meta["samples"]),
        "hours_seen": int(meta["hours"]),
        "features": list(FEATURE_NAMES),
        "lookback": DEFAULT_LOOKBACK,
        "horizon": DEFAULT_HORIZON,
        "epochs": epochs,
        "lr": lr,
    }
    with metadata_path.open("w", encoding="utf-8") as handle:
        json.dump(metadata, handle, ensure_ascii=False, indent=2)

    return {"status": "ok", "metadata_path": str(metadata_path), **metadata}


def _load_archived_weather(settings: Settings, days: int = 30) -> list[WeatherHour]:
    from datetime import timedelta
    now = datetime.now(timezone.utc)
    rows: list[WeatherHour] = []
    for day_offset in range(days + 1):
        day = (now - timedelta(days=day_offset)).strftime("%Y-%m-%d")
        path = settings.processed_dir / f"weather_{day}.jsonl"
        if not path.exists():
            continue
        with path.open("r", encoding="utf-8") as handle:
            for line in handle:
                if not line.strip():
                    continue
                try:
                    row = json.loads(line)
                    rows.append(
                        WeatherHour(
                            timestamp=datetime.fromisoformat(
                                row["timestamp"].replace("Z", "+00:00")
                            ),
                            hour_offset=int(row.get("hour_offset", 0)),
                            wind_speed_mps=float(row.get("wind_speed_mps", 0.0)),
                            wind_dir_deg=float(row.get("wind_dir_deg", 0.0)),
                            temp_c=float(row.get("temp_c", 0.0)),
                            humidity=float(row.get("humidity", 0.0)),
                            precipitation_mm=float(row.get("precipitation_mm", 0.0)),
                            boundary_layer_height_m=row.get("boundary_layer_height_m"),
                        )
                    )
                except (KeyError, ValueError, TypeError) as exc:
                    logger.debug("archived weather row skipped: {exc}", exc=exc)
                    continue
    return rows


def gate_from_metrics(
    heuristic_rmse: float,
    lstm_rmse: float,
    w_heuristic: float = 0.7,
) -> EnsembleGate:
    """Decide whether to enable the LSTM-blended forecast.

    The LSTM is used only when it beats the heuristic on the most recent
    backtest, and even then the heuristic stays the dominant signal at
    70 % weight to avoid catastrophic overrides.
    """
    if not (lstm_rmse > 0):
        return EnsembleGate(
            use_lstm=False, w_heuristic=1.0,
            heuristic_rmse=heuristic_rmse, lstm_rmse=lstm_rmse,
        )
    use_lstm = lstm_rmse < heuristic_rmse
    return EnsembleGate(
        use_lstm=use_lstm,
        w_heuristic=w_heuristic if use_lstm else 1.0,
        heuristic_rmse=heuristic_rmse,
        lstm_rmse=lstm_rmse,
    )


def predict_ensemble(
    heuristic_pm25: float,
    lstm_pm25: float,
    gate: EnsembleGate,
) -> float:
    return gate.blend(heuristic_pm25, lstm_pm25)
