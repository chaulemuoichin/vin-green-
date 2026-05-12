"""LSTM-bridge math: feature matrix + ensemble gate."""

from __future__ import annotations

from datetime import datetime, timedelta, timezone

from hanoi_air.lstm_wire import (
    DEFAULT_HORIZON,
    DEFAULT_LOOKBACK,
    FEATURE_NAMES,
    EnsembleGate,
    build_training_matrix,
    gate_from_metrics,
    predict_ensemble,
)
from hanoi_air.schemas import AirReading, WeatherHour


def _make_synthetic_archive(hours: int) -> tuple[list[AirReading], list[WeatherHour]]:
    start = datetime(2026, 5, 1, 0, tzinfo=timezone.utc)
    readings: list[AirReading] = []
    weather: list[WeatherHour] = []
    for i in range(hours):
        ts = start + timedelta(hours=i)
        readings.append(AirReading(
            timestamp=ts, source="OpenAQ", station_id="s1", station_name="Test",
            lat=21.03, lon=105.83, district="Hoàn Kiếm",
            pollutant="pm25", concentration=30.0 + (i % 12) * 1.5, aqi=None,
        ))
        weather.append(WeatherHour(
            timestamp=ts, hour_offset=i, wind_speed_mps=2.5 + 0.1 * (i % 6),
            wind_dir_deg=90.0 + 5.0 * (i % 4), temp_c=24.0 + (i % 8) * 0.5,
            humidity=68.0 + (i % 5) * 2.0,
        ))
    return readings, weather


def test_build_training_matrix_shapes() -> None:
    readings, weather = _make_synthetic_archive(hours=72)
    x, y, meta = build_training_matrix(readings, weather)
    assert meta["ok"] is True
    assert x.shape[1] == DEFAULT_LOOKBACK
    assert x.shape[2] == len(FEATURE_NAMES)
    assert y.shape[1] == DEFAULT_HORIZON
    assert x.shape[0] == y.shape[0]
    assert x.shape[0] == 72 - DEFAULT_LOOKBACK - DEFAULT_HORIZON + 1


def test_build_training_matrix_too_short_returns_not_ok() -> None:
    readings, weather = _make_synthetic_archive(hours=12)
    x, y, meta = build_training_matrix(readings, weather)
    assert meta["ok"] is False
    assert x.shape[0] == 0
    assert y.shape[0] == 0


def test_gate_disables_lstm_when_worse() -> None:
    gate = gate_from_metrics(heuristic_rmse=12.0, lstm_rmse=14.5)
    assert gate.use_lstm is False
    assert gate.w_heuristic == 1.0


def test_gate_enables_lstm_when_better() -> None:
    gate = gate_from_metrics(heuristic_rmse=14.0, lstm_rmse=10.5)
    assert gate.use_lstm is True
    assert 0 < gate.w_heuristic < 1


def test_gate_handles_zero_lstm_rmse_as_no_signal() -> None:
    gate = gate_from_metrics(heuristic_rmse=12.0, lstm_rmse=0.0)
    assert gate.use_lstm is False


def test_predict_ensemble_falls_back_to_heuristic_when_lstm_disabled() -> None:
    gate = EnsembleGate(
        use_lstm=False, w_heuristic=1.0,
        heuristic_rmse=10.0, lstm_rmse=15.0,
    )
    blended = predict_ensemble(heuristic_pm25=40.0, lstm_pm25=80.0, gate=gate)
    assert blended == 40.0


def test_predict_ensemble_blends_when_lstm_enabled() -> None:
    gate = gate_from_metrics(heuristic_rmse=12.0, lstm_rmse=9.5, w_heuristic=0.7)
    blended = predict_ensemble(heuristic_pm25=40.0, lstm_pm25=80.0, gate=gate)
    # 0.7 * 40 + 0.3 * 80 = 28 + 24 = 52
    assert abs(blended - 52.0) < 1e-6
