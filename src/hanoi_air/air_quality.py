from __future__ import annotations

from collections.abc import Iterable

Breakpoint = tuple[float, float, int, int]

# PM2.5 breakpoints are close to the US EPA NowCast scale and work well for
# dashboard triage. The app labels the result as operational AQI, not a
# regulatory VN_AQI calculation.
PM25_BREAKPOINTS: Iterable[Breakpoint] = (
    (0.0, 12.0, 0, 50),
    (12.1, 35.4, 51, 100),
    (35.5, 55.4, 101, 150),
    (55.5, 150.4, 151, 200),
    (150.5, 250.4, 201, 300),
    (250.5, 500.4, 301, 500),
)

NO2_BREAKPOINTS: Iterable[Breakpoint] = (
    (0.0, 40.0, 0, 50),
    (40.1, 100.0, 51, 100),
    (100.1, 200.0, 101, 150),
    (200.1, 400.0, 151, 200),
    (400.1, 800.0, 201, 300),
    (800.1, 1600.0, 301, 500),
)


def _linear_aqi(value: float, breakpoints: Iterable[Breakpoint]) -> int:
    value = max(0.0, float(value))
    last = None
    for c_low, c_high, i_low, i_high in breakpoints:
        last = (c_low, c_high, i_low, i_high)
        if c_low <= value <= c_high:
            return round((i_high - i_low) / (c_high - c_low) * (value - c_low) + i_low)
    assert last is not None
    c_low, c_high, i_low, i_high = last
    return min(500, round((i_high - i_low) / (c_high - c_low) * (value - c_low) + i_low))


def aqi_from_pm25(pm25: float) -> int:
    return _linear_aqi(pm25, PM25_BREAKPOINTS)


def aqi_from_no2(no2: float) -> int:
    return _linear_aqi(no2, NO2_BREAKPOINTS)


def combined_aqi(pm25: float | None = None, no2: float | None = None) -> int:
    values = []
    if pm25 is not None:
        values.append(aqi_from_pm25(pm25))
    if no2 is not None:
        values.append(aqi_from_no2(no2))
    return max(values) if values else 0


def aqi_category(aqi: int) -> str:
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


def health_recommendation(aqi: int) -> str:
    if aqi <= 50:
        return "có thể hoạt động ngoài trời"
    if aqi <= 100:
        return "người nhạy cảm nên theo dõi triệu chứng"
    if aqi <= 150:
        return "người nhạy cảm nên giảm vận động ngoài trời"
    if aqi <= 200:
        return "đeo khẩu trang và hạn chế hoạt động ngoài trời"
    if aqi <= 300:
        return "tránh hoạt động ngoài trời kéo dài"
    return "ở trong nhà và dùng lọc không khí nếu có"
