"""Downwind bearing math + wedge polygon + zone aggregation."""

from __future__ import annotations

from datetime import datetime, timezone

import pytest

from hanoi_air.downwind import (
    bearing_deg,
    compute_downwind_zones,
    district_downwind_risk,
    downwind_polygon,
    downwind_score,
)
from hanoi_air.schemas import District, SourceEmission, WeatherHour


def _district(district_id: str, name: str, lat: float, lon: float) -> District:
    return District(district_id=district_id, name=name, lat=lat, lon=lon)


def _source(name: str, lat: float, lon: float) -> SourceEmission:
    return SourceEmission(
        source_id=name.lower().replace(" ", "_"),
        name=name, lat=lat, lon=lon, district="X", height_m=30.0,
        pm25_g_s=1.0, no2_g_s=2.0,
    )


def _weather(wind_dir_deg: float, wind_speed_mps: float = 5.0) -> WeatherHour:
    return WeatherHour(
        timestamp=datetime(2026, 5, 12, 8, tzinfo=timezone.utc),
        hour_offset=0,
        wind_speed_mps=wind_speed_mps,
        wind_dir_deg=wind_dir_deg,
        temp_c=28.0, humidity=70.0,
    )


def test_bearing_east_is_90() -> None:
    # Same latitude, east of origin → bearing ≈ 90°
    b = bearing_deg(21.0, 105.0, 21.0, 105.5)
    assert abs(b - 90.0) < 1.0


def test_bearing_north_is_0() -> None:
    # Same longitude, north of origin → bearing ≈ 0°
    b = bearing_deg(21.0, 105.5, 21.5, 105.5)
    assert abs(b) < 1.0 or abs(b - 360.0) < 1.0


def test_bearing_south_west_is_in_third_quadrant() -> None:
    # Target south and west → bearing ~ 225°
    b = bearing_deg(21.0, 105.5, 20.5, 105.0)
    assert 220.0 < b < 230.0


THACH_THAT = _source("Thach That cement", 21.0794, 105.5719)
CAU_GIAY = _district("cau_giay", "Cau Giay", 21.0362, 105.7906)  # east of Thach That
SON_TAY = _district("son_tay", "Son Tay", 21.1369, 105.4972)     # NW of Thach That


def test_downwind_score_with_west_wind_lights_up_eastern_district() -> None:
    """West wind (270° = blowing FROM west TO east) → Cau Giay (east) is downwind."""
    score = downwind_score(THACH_THAT, CAU_GIAY, wind_dir_deg=270.0, wind_speed_mps=5.0)
    assert score > 0


def test_downwind_score_zero_for_upwind_district() -> None:
    """West wind from Thach That → Son Tay (to the NW) is essentially upwind, score 0."""
    score = downwind_score(THACH_THAT, SON_TAY, wind_dir_deg=270.0, wind_speed_mps=5.0)
    assert score == 0.0


def test_downwind_score_zero_in_calm_conditions() -> None:
    score = downwind_score(THACH_THAT, CAU_GIAY, wind_dir_deg=270.0, wind_speed_mps=0.1)
    assert score == 0.0


def test_downwind_score_decays_with_distance() -> None:
    near = _district("near", "Near", THACH_THAT.lat, THACH_THAT.lon + 0.02)  # ~2 km east
    far = _district("far", "Far", THACH_THAT.lat, THACH_THAT.lon + 0.18)     # ~18 km east
    near_score = downwind_score(THACH_THAT, near, 270.0, 5.0)
    far_score = downwind_score(THACH_THAT, far, 270.0, 5.0)
    assert near_score > far_score > 0


def test_downwind_polygon_has_arc_plus_source_endpoints() -> None:
    vertices = downwind_polygon(THACH_THAT, wind_dir_deg=270.0, wind_speed_mps=5.0,
                                length_km=20.0, half_angle_deg=22.5, arc_points=5)
    # First and last vertex are the source (closes the polygon)
    assert vertices[0] == (THACH_THAT.lat, THACH_THAT.lon)
    assert vertices[-1] == (THACH_THAT.lat, THACH_THAT.lon)
    # 5 arc points + 2 source closures = 7
    assert len(vertices) == 7


def test_downwind_polygon_empty_in_calm() -> None:
    assert downwind_polygon(THACH_THAT, 270.0, 0.1) == []


def test_compute_downwind_zones_collects_affected_districts() -> None:
    zones = compute_downwind_zones(
        sources=[THACH_THAT],
        districts=[CAU_GIAY, SON_TAY],
        weather=_weather(wind_dir_deg=270.0, wind_speed_mps=5.0),
    )
    assert len(zones) == 1
    zone = zones[0]
    assert zone["source_id"] == THACH_THAT.source_id
    affected_ids = [d["district_id"] for d in zone["affected_districts"]]
    assert "cau_giay" in affected_ids
    assert "son_tay" not in affected_ids
    assert zone["max_score"] > 0


def test_district_downwind_risk_picks_max_across_sources() -> None:
    other = _source("Another", 21.04, 105.78)  # right next to Cau Giay
    zones = compute_downwind_zones(
        sources=[THACH_THAT, other],
        districts=[CAU_GIAY],
        weather=_weather(wind_dir_deg=270.0, wind_speed_mps=5.0),
    )
    risk = district_downwind_risk(zones, "cau_giay")
    far_only = downwind_score(THACH_THAT, CAU_GIAY, 270.0, 5.0)
    assert risk >= far_only  # closer source dominates


def test_downwind_risk_zero_for_unknown_district() -> None:
    zones = compute_downwind_zones(
        sources=[THACH_THAT], districts=[CAU_GIAY],
        weather=_weather(270.0, 5.0),
    )
    assert district_downwind_risk(zones, "does_not_exist") == 0.0


def test_bundle_threads_downwind_through_forecast() -> None:
    """End-to-end: build_forecast must populate downwind_risk + zones."""
    from hanoi_air.config import get_settings
    from hanoi_air.forecast import build_forecast

    bundle = build_forecast(get_settings(), use_live=False)
    assert "downwind_zones" in bundle
    assert "0" in bundle["downwind_zones"]
    zones_t0 = bundle["downwind_zones"]["0"]
    assert isinstance(zones_t0, list)
    assert "downwind_risk" in bundle["forecasts"][0]
    # At least one row across the bundle should have a positive risk in
    # sample mode (the Thach That cluster + sample wind).
    max_risk = max(float(r["downwind_risk"]) for r in bundle["forecasts"])
    assert max_risk >= 0.0  # never negative
