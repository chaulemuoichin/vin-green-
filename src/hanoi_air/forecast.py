from __future__ import annotations

import math
from collections.abc import Iterable
from datetime import datetime, timedelta, timezone

from .air_quality import aqi_category, combined_aqi, health_recommendation
from .alerts import generate_alerts
from .cache import load_cache, save_cache
from .config import Settings, get_settings
from .dispersion import plume_contribution
from .geography import load_districts
from .ingestion import (
    fetch_open_meteo_air_forecast,
    fetch_regional_cities_aqi,
    fetch_regional_wind_grid,
    load_air_readings,
    load_sources,
    load_traffic,
    load_weather_forecast,
)
from .interpolation import kriging_or_idw
from .schemas import AirQualityForecast, AirReading, District, DistrictForecast, utc_now
from .sources import load_source_status, registry_as_dict
from .weather import wind_components, wind_direction_text


def build_forecast(
    settings: Settings | None = None,
    now: datetime | None = None,
    use_live: bool | None = None,
) -> dict:
    settings = settings or get_settings()
    now = now or utc_now()
    live_enabled = settings.use_live_data if use_live is None else use_live
    districts = load_districts(settings.sample_dir / "districts.csv")
    readings = load_air_readings(settings, use_live=live_enabled)
    weather_hours = load_weather_forecast(settings, now=now, use_live=live_enabled)
    air_background_rows = (
        fetch_open_meteo_air_forecast(settings, now=now, districts=districts)
        if live_enabled
        else []
    )
    sources = load_sources(settings)
    traffic = load_traffic(settings)
    wind_grid = fetch_regional_wind_grid(settings, now) if live_enabled else []
    regional_cities = fetch_regional_cities_aqi(settings, now) if live_enabled else []

    pm25_current = _interpolated_current(readings, districts, "pm25", default=38.0)
    no2_current = _interpolated_current(readings, districts, "no2", default=70.0)
    background = _background_by_district_hour(air_background_rows)
    pm25_bias = _district_bias(readings, background, districts, "pm25")
    no2_bias = _district_bias(readings, background, districts, "no2")
    mode = _forecast_mode(readings, air_background_rows)

    rows: list[DistrictForecast] = []
    for hour_offset in range(settings.forecast_horizon_hours):
        weather = weather_hours[min(hour_offset, len(weather_hours) - 1)]
        for district in districts:
            receptor_lat, receptor_lon = _receptor_for_district(district)
            plume = plume_contribution(
                sources,
                receptor_lat,
                receptor_lon,
                weather.wind_speed_mps,
                weather.wind_dir_deg,
            )
            traffic_profile = traffic.get(district.name, {})
            timestamp = weather.timestamp
            local_hour = _hanoi_hour(timestamp)
            traffic_factor = _traffic_hour_factor(local_hour)
            season = _seasonal_factor(timestamp)
            ventilation = _ventilation_factor(weather.wind_speed_mps, weather.humidity)
            diurnal = _diurnal_factor(local_hour)

            traffic_pm25 = float(traffic_profile.get("pm25_index", 0.6)) * traffic_factor
            traffic_no2 = float(traffic_profile.get("no2_index", 1.0)) * traffic_factor
            background_row = background.get((district.district_id, hour_offset))
            obs_pm25 = pm25_current[district.district_id] * diurnal * season * ventilation
            obs_no2 = (
                no2_current[district.district_id] * (0.82 + 0.18 * traffic_factor) * ventilation
            )
            if background_row:
                corrected_pm25 = max(
                    0.0, background_row.pm25 + pm25_bias.get(district.district_id, 0.0)
                )
                corrected_no2 = max(
                    0.0, background_row.no2 + no2_bias.get(district.district_id, 0.0)
                )
                pm25_base = 0.55 * obs_pm25 + 0.45 * corrected_pm25
                no2_base = 0.55 * obs_no2 + 0.45 * corrected_no2
            else:
                pm25_base = obs_pm25
                no2_base = obs_no2
            pm25 = pm25_base + traffic_pm25 + 0.46 * plume["pm25"]
            no2 = no2_base + traffic_no2 + 0.34 * plume["no2"]
            pm25 = max(4.0, min(pm25, 220.0))
            no2 = max(5.0, min(no2, 900.0))
            aqi = combined_aqi(pm25=pm25, no2=no2)
            uncertainty = _uncertainty_band(aqi, hour_offset, plume["pm25"])
            wind_u, wind_v = wind_components(weather.wind_speed_mps, weather.wind_dir_deg)
            rows.append(
                DistrictForecast(
                    district_id=district.district_id,
                    district_name=district.name,
                    timestamp=timestamp,
                    hour_offset=hour_offset,
                    pm25=round(pm25, 1),
                    no2=round(no2, 1),
                    aqi=aqi,
                    category=aqi_category(aqi),
                    wind_speed_mps=round(weather.wind_speed_mps, 2),
                    wind_dir_deg=round(weather.wind_dir_deg, 1),
                    wind_u=round(wind_u, 3),
                    wind_v=round(wind_v, 3),
                    plume_pm25=round(plume["pm25"], 1),
                    traffic_index=round(float(traffic_profile.get("congestion", 0.25)), 2),
                    uncertainty_low=max(0, round(aqi - uncertainty)),
                    uncertainty_high=min(500, round(aqi + uncertainty)),
                    health_text=_health_text(district, weather.wind_dir_deg, aqi),
                )
            )

    forecast_rows = [row.to_dict() for row in rows]
    alerts = generate_alerts(
        forecast_rows,
        aqi_threshold=settings.alert_aqi_threshold,
        pm25_threshold=settings.alert_pm25_threshold,
    )
    max_aqi = max(row["aqi"] for row in forecast_rows) if forecast_rows else 0
    return {
        "generated_at": now.isoformat(),
        "mode": mode,
        "horizon_hours": settings.forecast_horizon_hours,
        "district_count": len(districts),
        "max_aqi": max_aqi,
        "forecasts": forecast_rows,
        "alerts": [alert.to_dict() for alert in alerts],
        "sources": [source.to_dict() for source in sources],
        "wind_grid": wind_grid,
        "regional_cities": regional_cities,
        "source_registry": registry_as_dict(),
        "source_status": load_source_status(settings),
        "input_quality": _quality_summary(readings, air_background_rows),
    }


def build_cached_forecast(
    settings: Settings | None = None,
    force_refresh: bool = False,
    use_live: bool | None = None,
) -> dict:
    settings = settings or get_settings()
    if not force_refresh:
        cached = load_cache("forecast", settings)
        if cached:
            return cached
    forecast = build_forecast(settings, use_live=use_live)
    save_cache(forecast, "forecast", settings)
    return forecast


def top_n_worst(bundle: dict, n: int = 5, target_day: str = "tomorrow") -> list[dict]:
    rows = bundle.get("forecasts", [])
    if not rows:
        return []
    max_by_district: dict[str, dict] = {}
    for row in rows:
        if target_day == "tomorrow" and int(row["hour_offset"]) < 12:
            continue
        current = max_by_district.get(row["district_id"])
        if current is None or int(row["aqi"]) > int(current["aqi"]):
            max_by_district[row["district_id"]] = row
    if not max_by_district:
        for row in rows:
            current = max_by_district.get(row["district_id"])
            if current is None or int(row["aqi"]) > int(current["aqi"]):
                max_by_district[row["district_id"]] = row
    return sorted(max_by_district.values(), key=lambda r: int(r["aqi"]), reverse=True)[:n]


def _interpolated_current(
    readings: Iterable[AirReading], districts: Iterable[District], pollutant: str, default: float
) -> dict[str, float]:
    district_list = list(districts)
    points = [
        {"lat": r.lat, "lon": r.lon, "value": r.concentration}
        for r in readings
        if r.pollutant == pollutant and r.concentration > 0
    ]
    if not points:
        return {district.district_id: default for district in district_list}
    targets = [{"lat": district.lat, "lon": district.lon} for district in district_list]
    values = kriging_or_idw(points, targets)
    return {
        district.district_id: (float(value) if math.isfinite(value) else default)
        for district, value in zip(district_list, values, strict=True)
    }


def _quality_summary(
    readings: Iterable[AirReading], air_background_rows: Iterable[AirQualityForecast] = ()
) -> dict:
    items = list(readings)
    flags: dict[str, int] = {}
    sources: dict[str, int] = {}
    for reading in items:
        flags[reading.quality_flag] = flags.get(reading.quality_flag, 0) + 1
        sources[reading.source] = sources.get(reading.source, 0) + 1
    background_items = list(air_background_rows)
    if background_items:
        flags["forecast_background"] = flags.get("forecast_background", 0) + len(background_items)
        sources["Open-Meteo Air Quality"] = sources.get("Open-Meteo Air Quality", 0) + len(
            background_items
        )
    return {
        "reading_count": len(items),
        "air_background_count": len(background_items),
        "quality_flags": flags,
        "sources": sources,
    }


def _background_by_district_hour(
    rows: Iterable[AirQualityForecast],
) -> dict[tuple[str, int], AirQualityForecast]:
    return {(row.district_id, row.hour_offset): row for row in rows}


def _district_bias(
    readings: Iterable[AirReading],
    background: dict[tuple[str, int], AirQualityForecast],
    districts: Iterable[District],
    pollutant: str,
) -> dict[str, float]:
    district_by_name = {district.name: district.district_id for district in districts}
    sums: dict[str, tuple[float, int]] = {}
    for reading in readings:
        if reading.pollutant != pollutant:
            continue
        district_id = district_by_name.get(reading.district)
        if not district_id:
            continue
        background_row = background.get((district_id, 0))
        if not background_row:
            continue
        bg_value = background_row.pm25 if pollutant == "pm25" else background_row.no2
        diff = reading.concentration - bg_value
        total, count = sums.get(district_id, (0.0, 0))
        sums[district_id] = (total + diff, count + 1)
    return {
        district_id: max(-35.0, min(35.0, total / max(1, count)))
        for district_id, (total, count) in sums.items()
    }


def _forecast_mode(readings: Iterable[AirReading], background: Iterable[AirQualityForecast]) -> str:
    flags = {reading.quality_flag for reading in readings}
    has_background = any(True for _ in background)
    if flags & {"live_api", "public_crawl", "live", "fallback_live"}:
        return "live"
    if has_background:
        return "free_api_background"
    return "sample"


def _hanoi_hour(timestamp: datetime) -> int:
    if timestamp.tzinfo is None:
        timestamp = timestamp.replace(tzinfo=timezone.utc)
    return timestamp.astimezone(timezone(timedelta(hours=7))).hour


def _traffic_hour_factor(hour: int) -> float:
    if 7 <= hour <= 9 or 17 <= hour <= 19:
        return 1.15
    if hour >= 21 or hour <= 5:
        return 0.42
    return 0.72


def _diurnal_factor(hour: int) -> float:
    morning = math.exp(-((hour - 8.0) ** 2) / 18.0)
    evening = math.exp(-((hour - 18.0) ** 2) / 22.0)
    overnight = 0.18 if hour <= 5 or hour >= 22 else 0.0
    return 0.88 + 0.18 * morning + 0.16 * evening + overnight


def _seasonal_factor(timestamp: datetime) -> float:
    month = timestamp.month
    if month in {11, 12, 1, 2}:
        return 1.18
    if month in {3, 4, 10}:
        return 1.06
    if month in {6, 7, 8, 9}:
        return 0.94
    return 1.0


def _ventilation_factor(wind_speed_mps: float, humidity: float) -> float:
    stagnant = max(0.72, min(1.24, 1.14 - 0.07 * (wind_speed_mps - 2.0)))
    humid = 1.0 + max(0.0, humidity - 75.0) / 350.0
    return stagnant * humid


def _uncertainty_band(aqi: int, hour_offset: int, plume_pm25: float) -> float:
    return max(12.0, 0.20 * aqi, 8.0 + 0.45 * hour_offset + 0.25 * plume_pm25)


def _receptor_for_district(district: District) -> tuple[float, float]:
    receptors = {
        "bac_tu_liem": (21.0950, 105.7778),
        "long_bien": (21.0445, 105.9140),
        "hai_ba_trung": (21.0005, 105.8755),
    }
    return receptors.get(district.district_id, (district.lat, district.lon))


def _hotspot(district: District) -> str:
    hotspots = {
        "bac_tu_liem": "Cầu Thăng Long - Phạm Văn Đồng",
        "long_bien": "Thạch Bàn - logistics Long Biên",
        "thanh_xuan": "Nguyễn Trãi - Khuất Duy Tiến",
        "hoang_mai": "Giải Phóng - vành đai 3",
        "hai_ba_trung": "Minh Khai - Vĩnh Tuy",
        "hoan_kiem": "Cầu Chương Dương",
        "dong_da": "Ô Chợ Dừa - Ngã Tư Sở",
        "cau_giay": "Cầu Giấy - Xuân Thủy",
        "ha_dong": "Quang Trung - Lê Văn Lương",
        "nam_tu_liem": "Mỹ Đình - Lê Đức Thọ",
    }
    return hotspots.get(district.district_id, "khu vực thấp gió trong quận")


def _health_text(district: District, wind_dir_deg: float, aqi: int) -> str:
    return (
        f"{district.name}: {wind_direction_text(wind_dir_deg)} -> PM2.5 cao quanh "
        f"{_hotspot(district)}, AQI {aqi}, {health_recommendation(aqi)}."
    )
