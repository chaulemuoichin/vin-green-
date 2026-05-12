"""VN_AQI (QCVN 06:2022 / Decision 1459/QĐ-TCMT 2019) coverage."""

from __future__ import annotations

import pytest

from hanoi_air.vn_aqi import (
    vn_aqi_category,
    vn_aqi_color,
    vn_aqi_combined,
    vn_aqi_from_co,
    vn_aqi_from_no2,
    vn_aqi_from_o3,
    vn_aqi_from_pm10,
    vn_aqi_from_pm25,
    vn_aqi_from_so2,
)


@pytest.mark.parametrize(
    "pm25,expected_band",
    [
        (0.0, (0, 50)),
        (25.0, (0, 50)),
        (25.1, (51, 100)),
        (50.0, (51, 100)),
        (50.1, (101, 150)),
        (80.0, (101, 150)),
        (80.1, (151, 200)),
        (150.0, (151, 200)),
        (150.1, (201, 300)),
        (250.0, (201, 300)),
        (250.1, (301, 500)),
    ],
)
def test_pm25_breakpoints_land_in_band(pm25: float, expected_band: tuple[int, int]) -> None:
    aqi = vn_aqi_from_pm25(pm25)
    low, high = expected_band
    assert low <= aqi <= high, f"PM2.5 {pm25} → AQI {aqi} outside {expected_band}"


def test_pm25_category_labels_match_decision_1459() -> None:
    assert vn_aqi_category(vn_aqi_from_pm25(10.0)) == "Tốt"
    assert vn_aqi_category(vn_aqi_from_pm25(40.0)) == "Trung bình"
    assert vn_aqi_category(vn_aqi_from_pm25(65.0)) == "Kém"
    assert vn_aqi_category(vn_aqi_from_pm25(110.0)) == "Xấu"
    assert vn_aqi_category(vn_aqi_from_pm25(200.0)) == "Rất xấu"
    assert vn_aqi_category(vn_aqi_from_pm25(400.0)) == "Nguy hại"


def test_other_pollutants_use_distinct_breakpoints() -> None:
    # PM10 at 50 → boundary of Good
    assert 0 <= vn_aqi_from_pm10(50.0) <= 50
    # NO2 at 100 µg/m³ → boundary of Good
    assert 0 <= vn_aqi_from_no2(100.0) <= 50
    # O3 at 150 µg/m³ → Moderate band
    o3 = vn_aqi_from_o3(150.0)
    assert 51 <= o3 <= 100
    # CO 8h at 35 mg/m³ → Unhealthy for sensitive
    co = vn_aqi_from_co(35.0)
    assert 101 <= co <= 150
    # SO2 at 400 µg/m³ → Unhealthy for sensitive
    so2 = vn_aqi_from_so2(400.0)
    assert 101 <= so2 <= 150


def test_combined_takes_dominant_subindex() -> None:
    # PM2.5 60 → ~Kém (around 116); NO2 50 → Tốt (~25). Combined must follow PM2.5.
    combined = vn_aqi_combined(pm25=60.0, no2=50.0)
    pm_only = vn_aqi_from_pm25(60.0)
    assert combined == pm_only
    assert combined > vn_aqi_from_no2(50.0)


def test_combined_with_no_inputs_is_zero() -> None:
    assert vn_aqi_combined() == 0


def test_color_palette_is_six_distinct_bands() -> None:
    colors = {vn_aqi_color(aqi) for aqi in (25, 75, 125, 175, 250, 400)}
    assert len(colors) == 6
