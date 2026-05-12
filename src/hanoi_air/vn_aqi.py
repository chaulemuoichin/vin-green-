"""Vietnamese national air quality index (VN_AQI).

Breakpoints from Decision 1459/QĐ-TCMT (2019) issued by the Vietnam
Environment Administration, used in conjunction with QCVN 06:2022/BTNMT.
This is the regulatory scale referenced by Hanoi DONRE bulletins and is
distinct from the US-EPA NowCast scale exposed by :mod:`air_quality`.

Public API mirrors :mod:`air_quality` so callers can swap scales by
import alone.
"""

from __future__ import annotations

from collections.abc import Iterable

Breakpoint = tuple[float, float, int, int]

# PM2.5 — 24h average, µg/m³
PM25_BREAKPOINTS: Iterable[Breakpoint] = (
    (0.0, 25.0, 0, 50),
    (25.1, 50.0, 51, 100),
    (50.1, 80.0, 101, 150),
    (80.1, 150.0, 151, 200),
    (150.1, 250.0, 201, 300),
    (250.1, 500.0, 301, 500),
)

# PM10 — 24h average, µg/m³
PM10_BREAKPOINTS: Iterable[Breakpoint] = (
    (0.0, 50.0, 0, 50),
    (50.1, 150.0, 51, 100),
    (150.1, 250.0, 101, 150),
    (250.1, 350.0, 151, 200),
    (350.1, 420.0, 201, 300),
    (420.1, 500.0, 301, 500),
)

# NO2 — 1h average, µg/m³
NO2_BREAKPOINTS: Iterable[Breakpoint] = (
    (0.0, 100.0, 0, 50),
    (100.1, 200.0, 51, 100),
    (200.1, 700.0, 101, 150),
    (700.1, 1200.0, 151, 200),
    (1200.1, 2350.0, 201, 300),
    (2350.1, 3850.0, 301, 500),
)

# O3 — 1h average, µg/m³
O3_BREAKPOINTS: Iterable[Breakpoint] = (
    (0.0, 100.0, 0, 50),
    (100.1, 160.0, 51, 100),
    (160.1, 200.0, 101, 150),
    (200.1, 300.0, 151, 200),
    (300.1, 400.0, 201, 300),
    (400.1, 800.0, 301, 500),
)

# CO — 8h average, mg/m³
CO_BREAKPOINTS: Iterable[Breakpoint] = (
    (0.0, 10.0, 0, 50),
    (10.1, 30.0, 51, 100),
    (30.1, 45.0, 101, 150),
    (45.1, 60.0, 151, 200),
    (60.1, 90.0, 201, 300),
    (90.1, 120.0, 301, 500),
)

# SO2 — 1h average, µg/m³
SO2_BREAKPOINTS: Iterable[Breakpoint] = (
    (0.0, 125.0, 0, 50),
    (125.1, 350.0, 51, 100),
    (350.1, 550.0, 101, 150),
    (550.1, 800.0, 151, 200),
    (800.1, 1600.0, 201, 300),
    (1600.1, 2100.0, 301, 500),
)


def _linear_aqi(value: float, breakpoints: Iterable[Breakpoint]) -> int:
    value = max(0.0, float(value))
    last: Breakpoint | None = None
    for c_low, c_high, i_low, i_high in breakpoints:
        last = (c_low, c_high, i_low, i_high)
        if c_low <= value <= c_high:
            return round((i_high - i_low) / (c_high - c_low) * (value - c_low) + i_low)
    assert last is not None
    c_low, c_high, i_low, i_high = last
    return min(500, round((i_high - i_low) / (c_high - c_low) * (value - c_low) + i_low))


def vn_aqi_from_pm25(pm25: float) -> int:
    return _linear_aqi(pm25, PM25_BREAKPOINTS)


def vn_aqi_from_pm10(pm10: float) -> int:
    return _linear_aqi(pm10, PM10_BREAKPOINTS)


def vn_aqi_from_no2(no2: float) -> int:
    return _linear_aqi(no2, NO2_BREAKPOINTS)


def vn_aqi_from_o3(o3: float) -> int:
    return _linear_aqi(o3, O3_BREAKPOINTS)


def vn_aqi_from_co(co_mg: float) -> int:
    return _linear_aqi(co_mg, CO_BREAKPOINTS)


def vn_aqi_from_so2(so2: float) -> int:
    return _linear_aqi(so2, SO2_BREAKPOINTS)


def vn_aqi_combined(
    pm25: float | None = None,
    no2: float | None = None,
    pm10: float | None = None,
    o3: float | None = None,
    co_mg: float | None = None,
    so2: float | None = None,
) -> int:
    """Return the dominant sub-index, matching VN_AQI day reporting."""
    values: list[int] = []
    if pm25 is not None:
        values.append(vn_aqi_from_pm25(pm25))
    if pm10 is not None:
        values.append(vn_aqi_from_pm10(pm10))
    if no2 is not None:
        values.append(vn_aqi_from_no2(no2))
    if o3 is not None:
        values.append(vn_aqi_from_o3(o3))
    if co_mg is not None:
        values.append(vn_aqi_from_co(co_mg))
    if so2 is not None:
        values.append(vn_aqi_from_so2(so2))
    return max(values) if values else 0


def vn_aqi_category(aqi: int) -> str:
    if aqi <= 50:
        return "Tốt"
    if aqi <= 100:
        return "Trung bình"
    if aqi <= 150:
        return "Kém"
    if aqi <= 200:
        return "Xấu"
    if aqi <= 300:
        return "Rất xấu"
    return "Nguy hại"


def vn_aqi_color(aqi: int) -> str:
    """Hex color per Decision 1459 reporting palette."""
    if aqi <= 50:
        return "#00e400"
    if aqi <= 100:
        return "#ffff00"
    if aqi <= 150:
        return "#ff7e00"
    if aqi <= 200:
        return "#ff0000"
    if aqi <= 300:
        return "#8f3f97"
    return "#7e0023"


def vn_health_recommendation(aqi: int) -> str:
    """Citizen-facing guidance (Vietnamese)."""
    if aqi <= 50:
        return "chất lượng không khí tốt, có thể hoạt động ngoài trời bình thường"
    if aqi <= 100:
        return "chấp nhận được; nhóm nhạy cảm nên giảm hoạt động kéo dài"
    if aqi <= 150:
        return "nhóm nhạy cảm nên hạn chế hoạt động ngoài trời, đeo khẩu trang"
    if aqi <= 200:
        return "tất cả mọi người nên giảm vận động ngoài trời và đeo khẩu trang N95"
    if aqi <= 300:
        return "tránh hoạt động ngoài trời; đóng cửa sổ và dùng máy lọc không khí"
    return "ở trong nhà, đóng kín cửa, dùng máy lọc không khí và khẩu trang khi ra ngoài"
