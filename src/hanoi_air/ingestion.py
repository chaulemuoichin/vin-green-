from __future__ import annotations

import csv
import json
import math
import re
import time
import urllib.parse
from collections.abc import Iterable, Mapping, Sequence
from datetime import datetime, timedelta, timezone
from html import unescape
from pathlib import Path

from .air_quality import combined_aqi
from .archive import (
    append_processed_readings,
    archive_raw_payload,
    save_air_quality_forecast,
    save_weather_forecast,
)
from .config import HANOI_BOUNDS, Settings, get_settings
from .geography import load_districts, nearest_district
from .http import http_get_json as _http_json_impl
from .http import http_get_text as _http_text_impl
from .logging_setup import get_logger
from .retry import guard_source
from .schemas import AirQualityForecast, AirReading, District, SourceEmission, WeatherHour, utc_now
from .sources import mark_source_status, should_fetch_source, source_config

logger = get_logger(__name__)


def parse_datetime(value: str | None) -> datetime:
    if not value:
        return utc_now()
    normalized = value.replace("Z", "+00:00")
    return datetime.fromisoformat(normalized)


def _http_json(url: str, timeout: float = 12.0, headers: Mapping[str, str] | None = None) -> dict:
    """Thin wrapper preserving call-site signature; retries and pooling via hanoi_air.http."""
    return _http_json_impl(url, timeout=timeout, headers=headers)


def _http_text(url: str, timeout: float = 12.0) -> str:
    return _http_text_impl(url, timeout=timeout)


def parse_aqicn_payload(payload: dict) -> list[AirReading]:
    if payload.get("status") != "ok":
        return []
    data = payload.get("data") or {}
    city = data.get("city") or {}
    geo = city.get("geo") or [None, None]
    if geo[0] is None or geo[1] is None:
        return []
    lat = float(geo[0])
    lon = float(geo[1])
    district = nearest_district(lat, lon)
    timestamp = parse_datetime((data.get("time") or {}).get("iso"))
    station_id = f"aqicn_{data.get('idx', district.district_id)}"
    station_name = city.get("name") or district.name
    station_aqi = _safe_float(data.get("aqi"))
    readings: list[AirReading] = []
    iaqi = data.get("iaqi") or {}
    for raw_name, pollutant in {"pm25": "pm25", "pm2_5": "pm25", "no2": "no2"}.items():
        item = iaqi.get(raw_name)
        if not item:
            continue
        value = _safe_float(item.get("v"))
        if value is None:
            continue
        readings.append(
            AirReading(
                timestamp=timestamp,
                source="AQICN",
                station_id=station_id,
                station_name=station_name,
                lat=lat,
                lon=lon,
                district=district.name,
                pollutant=pollutant,
                concentration=value,
                aqi=station_aqi,
                quality_flag="live_api",
            )
        )
    return readings


def parse_openweather_air_payload(
    payload: dict, station_name: str = "OpenWeather"
) -> list[AirReading]:
    coord = payload.get("coord") or {}
    lat = _safe_float(coord.get("lat"))
    lon = _safe_float(coord.get("lon"))
    if lat is None or lon is None:
        return []
    district = nearest_district(lat, lon)
    readings: list[AirReading] = []
    aqi_scale = {1: 35, 2: 75, 3: 125, 4: 175, 5: 250}
    for item in payload.get("list") or []:
        timestamp = datetime.fromtimestamp(int(item.get("dt", 0)), timezone.utc)
        aqi = aqi_scale.get(int((item.get("main") or {}).get("aqi", 0)))
        components = item.get("components") or {}
        for raw_name, pollutant in {"pm2_5": "pm25", "no2": "no2"}.items():
            value = _safe_float(components.get(raw_name))
            if value is None:
                continue
            readings.append(
                AirReading(
                    timestamp=timestamp,
                    source="OpenWeather",
                    station_id=f"openweather_{district.district_id}",
                    station_name=station_name,
                    lat=lat,
                    lon=lon,
                    district=district.name,
                    pollutant=pollutant,
                    concentration=value,
                    aqi=aqi,
                    quality_flag="live_api",
                )
            )
    return readings


def build_open_meteo_weather_url(lat: float, lon: float, horizon_hours: int = 24) -> str:
    params = urllib.parse.urlencode(
        {
            "latitude": f"{lat:.5f}",
            "longitude": f"{lon:.5f}",
            "hourly": ",".join(
                [
                    "temperature_2m",
                    "relative_humidity_2m",
                    "precipitation",
                    "wind_speed_10m",
                    "wind_direction_10m",
                    "boundary_layer_height",
                ]
            ),
            "forecast_hours": horizon_hours,
            "timezone": "Asia/Bangkok",
            "wind_speed_unit": "ms",
        }
    )
    return f"https://api.open-meteo.com/v1/forecast?{params}"


def build_open_meteo_air_url(districts: Sequence[District], horizon_hours: int = 24) -> str:
    latitudes = ",".join(f"{district.lat:.5f}" for district in districts)
    longitudes = ",".join(f"{district.lon:.5f}" for district in districts)
    params = urllib.parse.urlencode(
        {
            "latitude": latitudes,
            "longitude": longitudes,
            "hourly": ",".join(
                [
                    "pm10",
                    "pm2_5",
                    "nitrogen_dioxide",
                    "aerosol_optical_depth",
                    "european_aqi",
                    "european_aqi_pm2_5",
                    "european_aqi_no2",
                ]
            ),
            "forecast_hours": horizon_hours,
            "timezone": "Asia/Bangkok",
            "domains": "auto",
        },
        safe=",",
    )
    return f"https://air-quality-api.open-meteo.com/v1/air-quality?{params}"


def parse_open_meteo_weather_payload(
    payload: dict, now: datetime | None = None, horizon_hours: int = 24
) -> list[WeatherHour]:
    now = now or utc_now()
    hourly = payload.get("hourly") or {}
    times = hourly.get("time") or []
    speed = hourly.get("wind_speed_10m") or []
    direction = hourly.get("wind_direction_10m") or []
    temp = hourly.get("temperature_2m") or []
    humidity = hourly.get("relative_humidity_2m") or []
    precipitation = hourly.get("precipitation") or []
    boundary = hourly.get("boundary_layer_height") or []
    rows: list[WeatherHour] = []
    for idx, value in enumerate(times[:horizon_hours]):
        try:
            timestamp = _parse_open_meteo_time(value)
            rows.append(
                WeatherHour(
                    timestamp=timestamp,
                    hour_offset=idx,
                    wind_speed_mps=float(speed[idx]),
                    wind_dir_deg=float(direction[idx]),
                    temp_c=float(temp[idx]),
                    humidity=float(humidity[idx]),
                    precipitation_mm=float(precipitation[idx]) if idx < len(precipitation) else 0.0,
                    boundary_layer_height_m=(
                        float(boundary[idx])
                        if idx < len(boundary) and boundary[idx] is not None
                        else None
                    ),
                )
            )
        except (ValueError, TypeError, IndexError, KeyError) as exc:
            logger.debug("open_meteo weather row {idx} skipped: {exc}", idx=idx, exc=exc)
            continue
    if rows:
        return rows
    return load_sample_weather_rows(now, horizon_hours)


def parse_open_meteo_air_payload(
    payload: object, districts: Sequence[District], horizon_hours: int = 24
) -> list[AirQualityForecast]:
    payloads = payload if isinstance(payload, list) else [payload]
    rows: list[AirQualityForecast] = []
    for district, district_payload in zip(districts, payloads, strict=False):
        if not isinstance(district_payload, dict):
            continue
        hourly = district_payload.get("hourly") or {}
        times = hourly.get("time") or []
        pm25 = hourly.get("pm2_5") or []
        no2 = hourly.get("nitrogen_dioxide") or []
        pm10 = hourly.get("pm10") or []
        aod = hourly.get("aerosol_optical_depth") or []
        for idx, value in enumerate(times[:horizon_hours]):
            try:
                rows.append(
                    AirQualityForecast(
                        district_id=district.district_id,
                        district_name=district.name,
                        timestamp=_parse_open_meteo_time(value),
                        hour_offset=idx,
                        pm25=float(pm25[idx]),
                        no2=float(no2[idx]),
                        pm10=(
                            float(pm10[idx]) if idx < len(pm10) and pm10[idx] is not None else None
                        ),
                        aerosol_optical_depth=(
                            float(aod[idx]) if idx < len(aod) and aod[idx] is not None else None
                        ),
                        source="Open-Meteo Air Quality",
                        quality_flag="forecast_background",
                    )
                )
            except (ValueError, TypeError, IndexError, KeyError) as exc:
                logger.debug(
                    "open_meteo air row {district}:{idx} skipped: {exc}",
                    district=district.district_id,
                    idx=idx,
                    exc=exc,
                )
                continue
    return rows


def parse_openaq_locations_payload(payload: dict) -> list[AirReading]:
    """Parse /v3/locations response — kept for backward-compat with sample fixtures."""
    readings: list[AirReading] = []
    for location in payload.get("results") or []:
        coords = location.get("coordinates") or {}
        lat = _safe_float(coords.get("latitude"))
        lon = _safe_float(coords.get("longitude"))
        if lat is None or lon is None:
            continue
        district = nearest_district(lat, lon)
        for sensor in location.get("sensors") or []:
            parameter = _normalize_pollutant_name((sensor.get("parameter") or {}).get("name"))
            if parameter not in {"pm25", "no2"}:
                continue
            latest = sensor.get("latest") or {}
            value = _safe_float(latest.get("value"))
            if value is None:
                continue
            readings.append(
                AirReading(
                    timestamp=_openaq_datetime(latest),
                    source="OpenAQ",
                    station_id=f"openaq_{sensor.get('id')}",
                    station_name=location.get("name") or district.name,
                    lat=lat,
                    lon=lon,
                    district=district.name,
                    pollutant=parameter,
                    concentration=value,
                    aqi=None,
                    quality_flag="live_api",
                )
            )
    return readings


def parse_openaq_sensor_measurement(
    payload: dict, sensor_id: int, station_name: str, lat: float, lon: float
) -> AirReading | None:
    """Parse /v3/sensors/{id}/measurements?limit=1 response into a single AirReading."""
    results = payload.get("results") or []
    if not results:
        return None
    item = results[0]
    value = _safe_float(item.get("value"))
    if value is None or value < 0:
        return None
    param_info = item.get("parameter") or {}
    parameter = _normalize_pollutant_name(param_info.get("name") or "")
    if parameter not in {"pm25", "no2"}:
        return None
    period = item.get("period") or {}
    dt_from = period.get("datetimeFrom") or {}
    ts_str = dt_from.get("utc") if isinstance(dt_from, dict) else None
    timestamp = parse_datetime(ts_str) if ts_str else utc_now()
    district = nearest_district(lat, lon)
    return AirReading(
        timestamp=timestamp,
        source="OpenAQ",
        station_id=f"openaq_{sensor_id}",
        station_name=station_name,
        lat=lat,
        lon=lon,
        district=district.name,
        pollutant=parameter,
        concentration=value,
        aqi=None,
        quality_flag="live_api",
    )


def parse_somo_html(html: str, site_id: str = "unknown") -> list[AirReading]:
    text = _html_to_text(html)
    aqi = _first_float_after(
        text, [r"\bAQI\s*([0-9]+(?:\.[0-9]+)?)", r"Chỉ\s*Số\s*([0-9]+(?:\.[0-9]+)?)"]
    )
    timestamp = _parse_vietnamese_public_time(text)
    temp = _first_float_after(text, [r"Nhiệt\s*độ\s*([0-9]+(?:\.[0-9]+)?)"])
    humidity = _first_float_after(text, [r"Độ\s*ẩm\s*([0-9]+(?:\.[0-9]+)?)"])
    pm25 = _first_float_after(
        text, [r"PM\s*2\.?5\s*([0-9]+(?:\.[0-9]+)?)", r"PM2\.5\s*([0-9]+(?:\.[0-9]+)?)"]
    )
    no2 = _first_float_after(
        text, [r"\bNO2\s*([0-9]+(?:\.[0-9]+)?)", r"\bNO₂\s*([0-9]+(?:\.[0-9]+)?)"]
    )
    lat, lon, district_name = _public_site_location(site_id)
    if pm25 is None and aqi is not None:
        pm25 = _pm25_from_operational_aqi(aqi)
    rows: list[AirReading] = []
    if pm25 is not None:
        rows.append(
            AirReading(
                timestamp=timestamp,
                source="SOMO",
                station_id=f"somo_site_{site_id}",
                station_name=f"SOMO public site {site_id}",
                lat=lat,
                lon=lon,
                district=district_name,
                pollutant="pm25",
                concentration=pm25,
                aqi=aqi,
                quality_flag="public_crawl",
            )
        )
    if no2 is not None:
        rows.append(
            AirReading(
                timestamp=timestamp,
                source="SOMO",
                station_id=f"somo_site_{site_id}",
                station_name=f"SOMO public site {site_id}",
                lat=lat,
                lon=lon,
                district=district_name,
                pollutant="no2",
                concentration=no2,
                aqi=aqi,
                quality_flag="public_crawl",
            )
        )
    if temp is not None or humidity is not None:
        pass
    return rows


def load_sample_readings(settings: Settings | None = None) -> list[AirReading]:
    settings = settings or get_settings()
    path = settings.sample_dir / "stations_current.csv"
    readings: list[AirReading] = []
    with path.open("r", encoding="utf-8", newline="") as handle:
        for row in csv.DictReader(handle):
            readings.append(
                AirReading(
                    timestamp=parse_datetime(row.get("timestamp")),
                    source=row["source"],
                    station_id=row["station_id"],
                    station_name=row["station_name"],
                    lat=float(row["lat"]),
                    lon=float(row["lon"]),
                    district=row["district"],
                    pollutant=row["pollutant"],
                    concentration=float(row["concentration"]),
                    aqi=_safe_float(row.get("aqi")),
                    quality_flag=row.get("quality_flag") or "sample",
                )
            )
    return readings


def load_somo_overrides(settings: Settings | None = None) -> list[dict]:
    settings = settings or get_settings()
    path = settings.sample_dir / "manual_somo_override.csv"
    if not path.exists():
        return []
    with path.open("r", encoding="utf-8", newline="") as handle:
        return list(csv.DictReader(handle))


def apply_manual_overrides(
    readings: list[AirReading], overrides: Iterable[dict]
) -> list[AirReading]:
    by_key: dict[tuple, dict] = {
        (row.get("station_id"), row.get("pollutant")): row for row in overrides
    }
    updated: list[AirReading] = []
    for reading in readings:
        override = by_key.get((reading.station_id, reading.pollutant))
        if not override:
            updated.append(reading)
            continue
        updated.append(
            AirReading(
                timestamp=parse_datetime(override.get("timestamp")),
                source=reading.source,
                station_id=reading.station_id,
                station_name=reading.station_name,
                lat=reading.lat,
                lon=reading.lon,
                district=reading.district,
                pollutant=reading.pollutant,
                concentration=float(override["concentration"]),
                aqi=_safe_float(override.get("aqi")),
                quality_flag=override.get("quality_flag") or "manual_override",
            )
        )
    return updated


_AQICN_HANOI_CITY_FEEDS = [
    ("https://api.waqi.info/feed/hanoi/", "Hoàn Kiếm"),
    ("https://api.waqi.info/feed/vietnam/hanoi-us-embassy/", "Ba Đình"),
    ("https://api.waqi.info/feed/vietnam/hanoi-ministry-of-science-technology/", "Đống Đa"),
    ("https://api.waqi.info/feed/vietnam/hanoi-cau-giay/", "Cầu Giấy"),
]


@guard_source("aqicn", fallback=[])
def fetch_aqicn_readings(settings: Settings | None = None) -> list[AirReading]:
    settings = settings or get_settings()
    config = source_config("aqicn")
    token = settings.aqicn_token or "demo"
    if not should_fetch_source("aqicn", settings):
        from .archive import load_recent_processed_readings

        cached = load_recent_processed_readings("AQICN", config.freshness_minutes, settings)
        if cached:
            return cached
    readings: list[AirReading] = []
    if settings.aqicn_token:
        for district in load_districts(settings.sample_dir / "districts.csv"):
            url = (
                "https://api.waqi.info/feed/geo:"
                f"{district.lat:.5f};{district.lon:.5f}/?"
                + urllib.parse.urlencode({"token": token})
            )
            try:
                payload = _http_json(url, timeout=config.timeout_seconds)
                archive_raw_payload("aqicn", payload, "json", settings)
                readings.extend(parse_aqicn_payload(payload))
            except Exception as exc:
                logger.warning(
                    "aqicn fetch failed for {district}: {exc}",
                    district=district.name,
                    exc=exc,
                )
                continue
    else:
        for feed_url, _ in _AQICN_HANOI_CITY_FEEDS:
            url = feed_url + "?" + urllib.parse.urlencode({"token": token})
            try:
                payload = _http_json(url, timeout=config.timeout_seconds)
                archive_raw_payload("aqicn", payload, "json", settings)
                readings.extend(parse_aqicn_payload(payload))
                time.sleep(0.3)
            except Exception as exc:
                logger.warning("aqicn demo feed {url} failed: {exc}", url=feed_url, exc=exc)
                continue
    append_processed_readings(readings, settings)
    mark_source_status("aqicn", bool(readings), len(readings), settings=settings)
    return readings


def fetch_openweather_readings(settings: Settings | None = None) -> list[AirReading]:
    settings = settings or get_settings()
    if not settings.openweather_api_key:
        return []
    readings: list[AirReading] = []
    for district in load_districts(settings.sample_dir / "districts.csv"):
        query = urllib.parse.urlencode(
            {"lat": district.lat, "lon": district.lon, "appid": settings.openweather_api_key}
        )
        url = f"https://api.openweathermap.org/data/2.5/air_pollution?{query}"
        try:
            readings.extend(parse_openweather_air_payload(_http_json(url), district.name))
        except Exception as exc:
            logger.warning(
                "openweather fetch failed for {district}: {exc}",
                district=district.name,
                exc=exc,
            )
            continue
    return readings


@guard_source("openaq", fallback=[])
def fetch_openaq_readings(settings: Settings | None = None) -> list[AirReading]:
    settings = settings or get_settings()
    config = source_config("openaq")
    if not settings.openaq_api_key:
        return []
    if not should_fetch_source("openaq", settings):
        from .archive import load_recent_processed_readings

        cached = load_recent_processed_readings("OpenAQ", config.freshness_minutes, settings)
        if cached:
            return cached
    bbox = f"{HANOI_BOUNDS['west']},{HANOI_BOUNDS['south']},{HANOI_BOUNDS['east']},{HANOI_BOUNDS['north']}"
    headers = {"X-API-Key": settings.openaq_api_key}
    try:
        locs_payload = _http_json(
            f"https://api.openaq.org/v3/locations?{urllib.parse.urlencode({'bbox': bbox, 'limit': 100}, safe=',')}",
            timeout=config.timeout_seconds,
            headers=headers,
        )
    except Exception as exc:
        mark_source_status("openaq", False, 0, str(exc), settings)
        return []
    readings: list[AirReading] = []
    for location in locs_payload.get("results") or []:
        coords = location.get("coordinates") or {}
        lat = _safe_float(coords.get("latitude"))
        lon = _safe_float(coords.get("longitude"))
        if lat is None or lon is None:
            continue
        station_name = location.get("name") or str(location.get("id"))
        for sensor in location.get("sensors") or []:
            param_name = _normalize_pollutant_name(
                (sensor.get("parameter") or {}).get("name") or ""
            )
            if param_name not in {"pm25", "no2"}:
                continue
            sensor_id = sensor.get("id")
            if not sensor_id:
                continue
            try:
                meas = _http_json(
                    f"https://api.openaq.org/v3/sensors/{sensor_id}/measurements?limit=1",
                    timeout=config.timeout_seconds,
                    headers=headers,
                )
                reading = parse_openaq_sensor_measurement(meas, sensor_id, station_name, lat, lon)
                if reading:
                    readings.append(reading)
                time.sleep(0.1)
            except Exception as exc:
                logger.debug(
                    "openaq sensor {sid} ({station}) fetch failed: {exc}",
                    sid=sensor_id,
                    station=station_name,
                    exc=exc,
                )
                continue
    archive_raw_payload("openaq", locs_payload, "json", settings)
    append_processed_readings(readings, settings)
    mark_source_status("openaq", bool(readings), len(readings), settings=settings)
    return readings


@guard_source("somo_crawler", fallback=[])
def fetch_somo_public_readings(settings: Settings | None = None) -> list[AirReading]:
    settings = settings or get_settings()
    config = source_config("somo_crawler")
    if not settings.enable_public_crawl:
        return []
    if not should_fetch_source("somo_crawler", settings):
        from .archive import load_recent_processed_readings

        return load_recent_processed_readings("SOMO", config.freshness_minutes, settings)
    readings: list[AirReading] = []
    site_ids = [item.strip() for item in settings.somo_site_ids.split(",") if item.strip()]
    for site_id in site_ids:
        url = f"https://moitruongthudo.vn/?{urllib.parse.urlencode({'site_id': site_id})}"
        try:
            html = _http_text(url, timeout=config.timeout_seconds)
            archive_raw_payload("somo_crawler", html, "html", settings)
            readings.extend(parse_somo_html(html, site_id))
            time.sleep(0.2)
        except Exception as exc:
            logger.warning(
                "somo crawler failed for site {site_id}: {exc}",
                site_id=site_id,
                exc=exc,
            )
            continue
    append_processed_readings(readings, settings)
    mark_source_status("somo_crawler", bool(readings), len(readings), settings=settings)
    return readings


def parse_cem_html(html: str) -> list[AirReading]:
    text = _html_to_text(html)
    rows: list[AirReading] = []
    pattern = re.compile(
        r"(?P<station>[\w\sÀ-ỹ\-.]{3,80})\s+(?P<time>\d{1,2}/\d{1,2}/\d{4}\s+\d{1,2}:\d{2})\s+(?P<aqi>\d{1,3})",
        re.IGNORECASE,
    )
    for match in pattern.finditer(text):
        aqi = float(match.group("aqi"))
        lat, lon, district_name = _public_site_location("cem")
        rows.append(
            AirReading(
                timestamp=_parse_public_time(match.group("time")),
                source="CEM",
                station_id=f"cem_{len(rows) + 1}",
                station_name=match.group("station").strip(),
                lat=lat,
                lon=lon,
                district=district_name,
                pollutant="pm25",
                concentration=_pm25_from_operational_aqi(aqi),
                aqi=aqi,
                quality_flag="public_crawl",
            )
        )
    return rows


@guard_source("cem_crawler", fallback=[])
def fetch_cem_public_readings(settings: Settings | None = None) -> list[AirReading]:
    settings = settings or get_settings()
    config = source_config("cem_crawler")
    if not settings.enable_public_crawl:
        return []
    if not should_fetch_source("cem_crawler", settings):
        from .archive import load_recent_processed_readings

        return load_recent_processed_readings("CEM", config.freshness_minutes, settings)
    try:
        html = _http_text("https://cem.gov.vn/", timeout=config.timeout_seconds)
        archive_raw_payload("cem_crawler", html, "html", settings)
        readings = parse_cem_html(html)
        append_processed_readings(readings, settings)
        mark_source_status("cem_crawler", bool(readings), len(readings), settings=settings)
        return readings
    except Exception as exc:
        logger.warning("CEM crawler failed: {exc}", exc=exc)
        mark_source_status("cem_crawler", False, 0, str(exc), settings)
        return []


def load_air_readings(
    settings: Settings | None = None, use_live: bool | None = None
) -> list[AirReading]:
    settings = settings or get_settings()
    live_enabled = settings.use_live_data if use_live is None else use_live
    readings: list[AirReading] = []
    if live_enabled:
        readings.extend(fetch_aqicn_readings(settings))
        readings.extend(fetch_openaq_readings(settings))
        readings.extend(fetch_somo_public_readings(settings))
        readings.extend(fetch_cem_public_readings(settings))
        if not readings:
            readings.extend(fetch_openweather_readings(settings))
    if not readings:
        readings = load_sample_readings(settings)
    return apply_manual_overrides(readings, load_somo_overrides(settings))


def load_weather_forecast(
    settings: Settings | None = None, now: datetime | None = None, use_live: bool = True
) -> list[WeatherHour]:
    settings = settings or get_settings()
    now = now or utc_now()
    if use_live and settings.use_live_data:
        weather = fetch_open_meteo_weather_forecast(settings, now)
        if weather:
            return weather
    return load_sample_weather_rows(now, settings.forecast_horizon_hours, settings)


def load_sample_weather_rows(
    now: datetime | None = None,
    horizon_hours: int = 24,
    settings: Settings | None = None,
) -> list[WeatherHour]:
    settings = settings or get_settings()
    now = now or utc_now()
    path = settings.sample_dir / "weather_forecast.csv"
    weather: list[WeatherHour] = []
    with path.open("r", encoding="utf-8", newline="") as handle:
        for row in csv.DictReader(handle):
            offset = int(row["hour_offset"])
            if offset >= horizon_hours:
                continue
            weather.append(
                WeatherHour(
                    timestamp=now + timedelta(hours=offset),
                    hour_offset=offset,
                    wind_speed_mps=float(row["wind_speed_mps"]),
                    wind_dir_deg=float(row["wind_dir_deg"]),
                    temp_c=float(row["temp_c"]),
                    humidity=float(row["humidity"]),
                    precipitation_mm=float(row.get("precipitation_mm") or 0.0),
                )
            )
    return weather


@guard_source("open_meteo_weather", fallback=[])
def fetch_open_meteo_weather_forecast(
    settings: Settings | None = None, now: datetime | None = None
) -> list[WeatherHour]:
    settings = settings or get_settings()
    now = now or utc_now()
    config = source_config("open_meteo_weather")
    from .cache import load_cache, save_cache

    cached = load_cache("open_meteo_weather_forecast", settings)
    if not should_fetch_source("open_meteo_weather", settings) and cached:
        return [_weather_hour_from_dict(row) for row in cached.get("hours", [])]
    hanoi_center = (21.0278, 105.8342)
    url = build_open_meteo_weather_url(
        hanoi_center[0], hanoi_center[1], horizon_hours=settings.forecast_horizon_hours
    )
    try:
        payload = _http_json(url, timeout=config.timeout_seconds)
        archive_raw_payload("open_meteo_weather", payload, "json", settings)
        rows = parse_open_meteo_weather_payload(payload, now, settings.forecast_horizon_hours)
        if rows:
            save_cache(
                {"hours": [row.to_dict() for row in rows]},
                "open_meteo_weather_forecast",
                settings,
                ttl_seconds=config.cadence_minutes * 60,
            )
            save_weather_forecast(rows, "open_meteo_weather", settings)
            mark_source_status("open_meteo_weather", True, len(rows), settings=settings)
            return rows
    except Exception as exc:
        logger.warning("open_meteo weather fetch failed: {exc}", exc=exc)
        mark_source_status("open_meteo_weather", False, 0, str(exc), settings)
    if cached:
        return [_weather_hour_from_dict(row) for row in cached.get("hours", [])]
    return []


@guard_source("open_meteo_air", fallback=[])
def fetch_open_meteo_air_forecast(
    settings: Settings | None = None,
    now: datetime | None = None,
    districts: Sequence[District] | None = None,
) -> list[AirQualityForecast]:
    settings = settings or get_settings()
    districts = list(districts or load_districts(settings.sample_dir / "districts.csv"))
    config = source_config("open_meteo_air")
    from .cache import load_cache, save_cache

    cached = load_cache("open_meteo_air_forecast", settings)
    if not should_fetch_source("open_meteo_air", settings) and cached:
        return [_air_quality_forecast_from_dict(row) for row in cached.get("rows", [])]
    url = build_open_meteo_air_url(districts, horizon_hours=settings.forecast_horizon_hours)
    try:
        payload = _http_json(url, timeout=config.timeout_seconds)
        archive_raw_payload("open_meteo_air", payload, "json", settings)
        rows = parse_open_meteo_air_payload(payload, districts, settings.forecast_horizon_hours)
        if rows:
            save_cache(
                {"rows": [row.to_dict() for row in rows]},
                "open_meteo_air_forecast",
                settings,
                ttl_seconds=config.cadence_minutes * 60,
            )
            save_air_quality_forecast(rows, "open_meteo_air", settings)
            mark_source_status("open_meteo_air", True, len(rows), settings=settings)
            return rows
    except Exception as exc:
        logger.warning("open_meteo air forecast failed: {exc}", exc=exc)
        mark_source_status("open_meteo_air", False, 0, str(exc), settings)
    if cached:
        return [_air_quality_forecast_from_dict(row) for row in cached.get("rows", [])]
    return []


def fetch_cems_sources(settings: Settings | None = None) -> list[SourceEmission]:
    settings = settings or get_settings()
    if not settings.cems_api_url:
        return []
    try:
        payload = _http_json(settings.cems_api_url)
    except Exception as exc:
        logger.warning("CEMS source fetch failed: {exc}", exc=exc)
        return []
    rows = payload.get("sources", payload if isinstance(payload, list) else [])
    sources: list[SourceEmission] = []
    for row in rows:
        try:
            sources.append(
                SourceEmission(
                    source_id=str(row.get("source_id") or row.get("id")),
                    name=str(row.get("name") or row.get("station_name") or "CEMS source"),
                    lat=float(row.get("lat") or row.get("latitude")),
                    lon=float(row.get("lon") or row.get("longitude")),
                    district=str(row.get("district") or ""),
                    height_m=float(row.get("height_m") or row.get("stack_height_m") or 35.0),
                    pm25_g_s=float(row.get("pm25_g_s") or row.get("pm25") or 0.0),
                    no2_g_s=float(row.get("no2_g_s") or row.get("no2") or 0.0),
                    status=str(row.get("status") or "active"),
                )
            )
        except (ValueError, TypeError, KeyError) as exc:
            logger.debug("CEMS row skipped: {exc} (row={row})", exc=exc, row=row)
            continue
    return sources


def load_sources(settings: Settings | None = None) -> list[SourceEmission]:
    settings = settings or get_settings()
    live_sources = fetch_cems_sources(settings)
    if live_sources:
        return live_sources
    path = settings.sample_dir / "factories.csv"
    sources: list[SourceEmission] = []
    with path.open("r", encoding="utf-8", newline="") as handle:
        for row in csv.DictReader(handle):
            sources.append(
                SourceEmission(
                    source_id=row["source_id"],
                    name=row["name"],
                    lat=float(row["lat"]),
                    lon=float(row["lon"]),
                    district=row["district"],
                    height_m=float(row["height_m"]),
                    pm25_g_s=float(row["pm25_g_s"]),
                    no2_g_s=float(row["no2_g_s"]),
                    status=row.get("status") or "active",
                )
            )
    return sources


def load_traffic(settings: Settings | None = None) -> dict[str, dict]:
    settings = settings or get_settings()
    path = settings.sample_dir / "traffic.csv"
    rows: list[dict] = []
    with path.open("r", encoding="utf-8", newline="") as handle:
        rows = list(csv.DictReader(handle))
    if settings.enable_overpass:
        rows = _apply_overpass_road_density(rows, settings)
    if settings.google_maps_api_key:
        rows = _apply_google_traffic_proxy(rows, settings.google_maps_api_key)

    by_district: dict[str, dict] = {}
    for row in rows:
        district = row["district"]
        entry = by_district.setdefault(
            district,
            {"pm25_index": 0.0, "no2_index": 0.0, "congestion": 0.0, "corridors": []},
        )
        congestion = float(row["congestion_default"])
        entry["pm25_index"] += float(row["pm25_index"]) * congestion
        entry["no2_index"] += float(row["no2_index"]) * congestion
        entry["congestion"] = max(entry["congestion"], congestion)
        entry["corridors"].append(row["name"])
    return by_district


def build_overpass_roads_url() -> str:
    query = f"""
    [out:json][timeout:45];
    (
      way["highway"~"motorway|trunk|primary|secondary|tertiary"]
        ({HANOI_BOUNDS['south']},{HANOI_BOUNDS['west']},{HANOI_BOUNDS['north']},{HANOI_BOUNDS['east']});
    );
    out geom;
    """
    return "https://overpass-api.de/api/interpreter?" + urllib.parse.urlencode({"data": query})


def parse_overpass_roads_payload(payload: dict) -> dict[str, float]:
    districts = load_districts()
    density: dict[str, float] = {district.name: 0.0 for district in districts}
    highway_weight = {
        "motorway": 1.4,
        "trunk": 1.25,
        "primary": 1.1,
        "secondary": 0.85,
        "tertiary": 0.65,
    }
    for element in payload.get("elements") or []:
        geometry = element.get("geometry") or []
        if len(geometry) < 2:
            continue
        tags = element.get("tags") or {}
        weight = highway_weight.get(str(tags.get("highway")), 0.45)
        lat = sum(float(point["lat"]) for point in geometry) / len(geometry)
        lon = sum(float(point["lon"]) for point in geometry) / len(geometry)
        district = nearest_district(lat, lon, districts)
        density[district.name] += max(0.05, len(geometry) / 10.0) * weight
    max_density = max(density.values()) if density else 0.0
    if max_density <= 0:
        return density
    return {district: value / max_density for district, value in density.items()}


def _apply_overpass_road_density(rows: list[dict], settings: Settings) -> list[dict]:
    from .cache import load_cache, save_cache

    config = source_config("overpass_roads")
    cached = load_cache("overpass_road_density", settings)
    density: dict[str, float] = dict(cached.get("density", {})) if cached else {}
    if not density and should_fetch_source("overpass_roads", settings):
        try:
            payload = _http_json(build_overpass_roads_url(), timeout=config.timeout_seconds)
            archive_raw_payload("overpass_roads", payload, "json", settings)
            density = parse_overpass_roads_payload(payload)
            save_cache(
                {"density": density},
                "overpass_road_density",
                settings,
                ttl_seconds=config.cadence_minutes * 60,
            )
            mark_source_status("overpass_roads", True, len(density), settings=settings)
        except Exception as exc:
            logger.warning("overpass roads fetch failed: {exc}", exc=exc)
            mark_source_status("overpass_roads", False, 0, str(exc), settings)
            density = {}
    if not density:
        return rows
    enriched: list[dict] = []
    for row in rows:
        updated = dict(row)
        multiplier = 0.75 + 0.45 * float(density.get(row["district"], 0.25))
        updated["pm25_index"] = f"{float(row['pm25_index']) * multiplier:.3f}"
        updated["no2_index"] = f"{float(row['no2_index']) * multiplier:.3f}"
        enriched.append(updated)
    return enriched


def _apply_google_traffic_proxy(rows: list[dict], api_key: str) -> list[dict]:
    enriched: list[dict] = []
    for row in rows:
        updated = dict(row)
        congestion = _google_corridor_congestion(row, api_key)
        if congestion is not None:
            updated["congestion_default"] = f"{congestion:.3f}"
        enriched.append(updated)
    return enriched


def _google_corridor_congestion(row: dict, api_key: str) -> float | None:
    lat = float(row["lat"])
    lon = float(row["lon"])
    destination = f"{lat + 0.012:.6f},{lon + 0.012:.6f}"
    params = urllib.parse.urlencode(
        {
            "origins": f"{lat:.6f},{lon:.6f}",
            "destinations": destination,
            "departure_time": int(time.time()),
            "key": api_key,
        }
    )
    url = f"https://maps.googleapis.com/maps/api/distancematrix/json?{params}"
    try:
        payload = _http_json(url, timeout=8)
        element = payload["rows"][0]["elements"][0]
        duration = float(element["duration"]["value"])
        traffic_duration = float(element.get("duration_in_traffic", element["duration"])["value"])
        ratio = traffic_duration / max(1.0, duration)
        return max(0.2, min(1.0, 0.35 + 0.45 * (ratio - 1.0)))
    except Exception as exc:
        logger.debug("google distance matrix corridor failed: {exc}", exc=exc)
        return None


def load_json(path: Path) -> dict:
    with path.open("r", encoding="utf-8") as handle:
        return json.load(handle)


def _parse_open_meteo_time(value: str) -> datetime:
    parsed = datetime.fromisoformat(str(value))
    if parsed.tzinfo is None:
        parsed = parsed.replace(tzinfo=timezone(timedelta(hours=7)))
    return parsed.astimezone(timezone.utc)


def _weather_hour_from_dict(row: Mapping[str, object]) -> WeatherHour:
    return WeatherHour(
        timestamp=parse_datetime(str(row["timestamp"])),
        hour_offset=int(row["hour_offset"]),
        wind_speed_mps=float(row["wind_speed_mps"]),
        wind_dir_deg=float(row["wind_dir_deg"]),
        temp_c=float(row["temp_c"]),
        humidity=float(row["humidity"]),
        precipitation_mm=float(row.get("precipitation_mm") or 0.0),
        boundary_layer_height_m=(
            float(row["boundary_layer_height_m"])
            if row.get("boundary_layer_height_m") is not None
            else None
        ),
    )


def _air_quality_forecast_from_dict(row: Mapping[str, object]) -> AirQualityForecast:
    return AirQualityForecast(
        district_id=str(row["district_id"]),
        district_name=str(row["district_name"]),
        timestamp=parse_datetime(str(row["timestamp"])),
        hour_offset=int(row["hour_offset"]),
        pm25=float(row["pm25"]),
        no2=float(row["no2"]),
        pm10=float(row["pm10"]) if row.get("pm10") is not None else None,
        aerosol_optical_depth=(
            float(row["aerosol_optical_depth"])
            if row.get("aerosol_optical_depth") is not None
            else None
        ),
        source=str(row.get("source") or "Open-Meteo Air Quality"),
        quality_flag=str(row.get("quality_flag") or "forecast_background"),
    )


def _normalize_pollutant_name(value: object) -> str:
    normalized = str(value or "").strip().lower().replace(".", "").replace("_", "")
    if normalized in {"pm25", "pm2 5", "pm2,5"}:
        return "pm25"
    if normalized in {"no2", "nitrogendioxide", "nitrogen dioxide"}:
        return "no2"
    return normalized


def _openaq_datetime(latest: Mapping[str, object]) -> datetime:
    value = latest.get("datetime")
    if isinstance(value, Mapping):
        return parse_datetime(str(value.get("utc") or value.get("local")))
    if value:
        return parse_datetime(str(value))
    return utc_now()


def _html_to_text(html: str) -> str:
    text = re.sub(r"<script\b[^>]*>.*?</script>", " ", html, flags=re.IGNORECASE | re.DOTALL)
    text = re.sub(r"<style\b[^>]*>.*?</style>", " ", text, flags=re.IGNORECASE | re.DOTALL)
    text = re.sub(r"<[^>]+>", " ", text)
    text = unescape(text)
    return re.sub(r"\s+", " ", text).strip()


def _first_float_after(text: str, patterns: Sequence[str]) -> float | None:
    for pattern in patterns:
        match = re.search(pattern, text, re.IGNORECASE)
        if match:
            return _safe_float(match.group(1))
    return None


def _parse_vietnamese_public_time(text: str) -> datetime:
    match = re.search(r"ngày\s+(\d{1,2}/\d{1,2}/\d{4})\s+(\d{1,2}:\d{2})", text, re.IGNORECASE)
    if match:
        return _parse_public_time(f"{match.group(1)} {match.group(2)}")
    match = re.search(r"(\d{1,2}/\d{1,2}/\d{4})\s+(\d{1,2}:\d{2})", text)
    if match:
        return _parse_public_time(f"{match.group(1)} {match.group(2)}")
    return utc_now()


def _parse_public_time(value: str) -> datetime:
    parsed = datetime.strptime(value.strip(), "%d/%m/%Y %H:%M")
    return parsed.replace(tzinfo=timezone(timedelta(hours=7))).astimezone(timezone.utc)


def _pm25_from_operational_aqi(aqi: float) -> float:
    aqi = max(0.0, min(float(aqi), 500.0))
    if aqi <= 50:
        return aqi / 50.0 * 12.0
    if aqi <= 100:
        return 12.1 + (aqi - 51.0) / 49.0 * (35.4 - 12.1)
    if aqi <= 150:
        return 35.5 + (aqi - 101.0) / 49.0 * (55.4 - 35.5)
    if aqi <= 200:
        return 55.5 + (aqi - 151.0) / 49.0 * (150.4 - 55.5)
    if aqi <= 300:
        return 150.5 + (aqi - 201.0) / 99.0 * (250.4 - 150.5)
    return 250.5 + (aqi - 301.0) / 199.0 * (500.4 - 250.5)


def _public_site_location(site_id: str) -> tuple[float, float, str]:
    site_map = {
        "1": (21.0288, 105.8522, "Hoàn Kiếm"),
        "39": (21.0362, 105.7906, "Cầu Giấy"),
        "cem": (21.0278, 105.8342, "Hoàn Kiếm"),
    }
    return site_map.get(str(site_id), (21.0278, 105.8342, "Hoàn Kiếm"))


def _safe_float(value: object) -> float | None:
    try:
        if value in {None, "", "-", "N/A"}:
            return None
        number = float(value)  # type: ignore[arg-type]
        if math.isnan(number):
            return None
        return number
    except (TypeError, ValueError):
        return None


def reading_aqi(reading: AirReading) -> int:
    if reading.aqi is not None:
        return round(reading.aqi)
    if reading.pollutant == "pm25":
        return combined_aqi(pm25=reading.concentration)
    if reading.pollutant == "no2":
        return combined_aqi(no2=reading.concentration)
    return 0
