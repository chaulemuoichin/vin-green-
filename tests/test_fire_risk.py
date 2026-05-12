"""Tests for hex grid fire risk scoring module."""
from __future__ import annotations

from datetime import datetime, timezone

import pytest

from hanoi_air.fire_risk import (
    DEFAULT_RISK_THRESHOLD,
    _distance_factor,
    _frp_factor,
    _upwind_factor,
    compute_risk_score,
    filter_fires_by_risk,
    fire_to_h3,
    load_hit_rates,
    update_hit_rate,
)
from hanoi_air.schemas import FireDetection, WeatherHour

_NOW = datetime(2026, 5, 12, 6, 0, tzinfo=timezone.utc)


def _make_fire(
    lat: float = 20.5,
    lon: float = 103.5,
    frp: float = 100.0,
    bearing: float = 270.0,
    distance: float = 250.0,
    confidence: str = "h",
) -> FireDetection:
    return FireDetection(
        fire_id=f"test_{lat}_{lon}",
        timestamp=_NOW,
        lat=lat,
        lon=lon,
        frp=frp,
        confidence=confidence,
        satellite="N20",
        distance_to_hanoi_km=distance,
        bearing_from_hanoi_deg=bearing,
        h3_index=fire_to_h3(lat, lon),
    )


def _make_weather(wind_dir_850: float = 90.0, wind_speed_850: float = 8.0) -> WeatherHour:
    """Wind from East (90°) → smoke travels West (270°)."""
    return WeatherHour(
        timestamp=_NOW,
        hour_offset=0,
        wind_speed_mps=5.0,
        wind_dir_deg=wind_dir_850,
        temp_c=28.0,
        humidity=65.0,
        wind_speed_850hpa_mps=wind_speed_850,
        wind_dir_850hpa_deg=wind_dir_850,
    )


class TestH3Mapping:
    def test_fire_to_h3_returns_resolution7(self) -> None:
        h = fire_to_h3(21.03, 105.85)
        assert len(h) == 15

    def test_nearby_fires_can_share_hex(self) -> None:
        h1 = fire_to_h3(20.500, 103.500)
        h2 = fire_to_h3(20.502, 103.502)
        # Very close fires may share the same hex (~5km cells)
        # Not guaranteed but at least valid hex strings
        assert len(h1) == 15
        assert len(h2) == 15

    def test_different_regions_have_different_hexes(self) -> None:
        h_laos = fire_to_h3(20.5, 103.5)
        h_myanmar = fire_to_h3(21.0, 102.0)
        assert h_laos != h_myanmar


class TestFactors:
    def test_distance_factor_decay(self) -> None:
        assert _distance_factor(0) == pytest.approx(1.0)
        assert _distance_factor(300) == pytest.approx(0.368, rel=0.01)
        assert _distance_factor(600) < 0.15

    def test_frp_factor_sigmoid(self) -> None:
        assert _frp_factor(10) < 0.2
        assert _frp_factor(100) == pytest.approx(0.5, rel=0.05)
        assert _frp_factor(300) > 0.85

    def test_upwind_factor_within_45deg(self) -> None:
        # Wind from East (90°) → smoke toward West (270°)
        # Fire bearing 270° from Hanoi = fire is to the West = upwind ✓
        assert _upwind_factor(270.0, 90.0) == pytest.approx(1.0)

    def test_upwind_factor_outside_45deg(self) -> None:
        # Fire bearing 180° (South), smoke travels West → not upwind
        assert _upwind_factor(180.0, 90.0) == pytest.approx(0.2)

    def test_upwind_factor_wraps_correctly(self) -> None:
        # Wind from NW (315°) → smoke toward SE (135°)
        # Fire bearing 135° = upwind ✓
        assert _upwind_factor(135.0, 315.0) == pytest.approx(1.0)


class TestRiskScore:
    def test_high_frp_close_upwind_high_score(self) -> None:
        fire = _make_fire(frp=200.0, distance=150.0, bearing=270.0)
        weather = _make_weather(wind_dir_850=90.0)  # smoke toward West (270°)
        hit_rates = {fire.h3_index: 0.8}
        score = compute_risk_score(fire, weather, hit_rates)
        assert score > DEFAULT_RISK_THRESHOLD

    def test_low_frp_far_crosswind_low_score(self) -> None:
        fire = _make_fire(frp=20.0, distance=580.0, bearing=180.0)
        weather = _make_weather(wind_dir_850=90.0)  # smoke toward West, fire is South
        hit_rates = {fire.h3_index: 0.3}
        score = compute_risk_score(fire, weather, hit_rates)
        assert score <= DEFAULT_RISK_THRESHOLD

    def test_score_uses_default_hit_rate_for_unknown_hex(self) -> None:
        fire = _make_fire()
        weather = _make_weather()
        score = compute_risk_score(fire, weather, {})  # empty hit_rates
        # Should still produce a valid score using the 0.5 default
        assert 0.0 <= score <= 1.0

    def test_score_bounded(self) -> None:
        fire = _make_fire(frp=500.0, distance=1.0, bearing=270.0)
        weather = _make_weather(wind_dir_850=90.0)
        hit_rates = {fire.h3_index: 1.0}
        score = compute_risk_score(fire, weather, hit_rates)
        assert 0.0 <= score <= 1.0


class TestFilterFiresByRisk:
    def test_splits_high_and_low_risk(self) -> None:
        fires = [
            _make_fire(frp=200.0, distance=150.0, bearing=270.0),  # high risk
            _make_fire(lat=19.0, lon=107.0, frp=15.0, distance=570.0, bearing=90.0),  # low risk
        ]
        weather = _make_weather(wind_dir_850=90.0)
        high, low = filter_fires_by_risk(fires, weather, risk_threshold=DEFAULT_RISK_THRESHOLD)

        assert len(high) + len(low) == len(fires)
        assert all(f.risk_score > DEFAULT_RISK_THRESHOLD for f in high)
        assert all(f.risk_score <= DEFAULT_RISK_THRESHOLD for f in low)

    def test_enriches_fires_with_h3_index(self) -> None:
        fire = FireDetection(
            fire_id="no_h3",
            timestamp=_NOW,
            lat=20.5,
            lon=103.5,
            frp=100.0,
            confidence="h",
            satellite="N20",
            distance_to_hanoi_km=250.0,
            bearing_from_hanoi_deg=270.0,
            h3_index="",  # empty
        )
        weather = _make_weather()
        high, low = filter_fires_by_risk([fire], weather)
        result_fire = (high + low)[0]
        assert len(result_fire.h3_index) == 15  # H3 resolution 7

    def test_empty_input_returns_empty_lists(self) -> None:
        high, low = filter_fires_by_risk([], _make_weather())
        assert high == []
        assert low == []


class TestHitRateUpdate:
    def test_update_increases_rate_on_pollution(self, tmp_path, monkeypatch) -> None:
        from hanoi_air.config import Settings

        settings = Settings(cache_dir=tmp_path)
        h3_index = fire_to_h3(20.5, 103.5)

        # Initial rate is the default (0.5)
        update_hit_rate(h3_index, caused_pollution=True, settings=settings)
        rates = load_hit_rates(settings)
        assert rates[h3_index] > 0.5

    def test_update_decreases_rate_on_no_pollution(self, tmp_path, monkeypatch) -> None:
        from hanoi_air.config import Settings

        settings = Settings(cache_dir=tmp_path)
        h3_index = fire_to_h3(20.5, 103.5)

        update_hit_rate(h3_index, caused_pollution=False, settings=settings)
        rates = load_hit_rates(settings)
        assert rates[h3_index] < 0.5
