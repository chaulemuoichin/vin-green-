from __future__ import annotations

from dataclasses import asdict, dataclass
from datetime import datetime, timezone
from typing import Any


def utc_now() -> datetime:
    return datetime.now(timezone.utc)


def isoformat(value: datetime) -> str:
    return value.isoformat()


@dataclass(frozen=True)
class District:
    district_id: str
    name: str
    lat: float
    lon: float
    population: int = 0
    area_km2: float = 0.0
    urban_level: str = "mixed"

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


@dataclass(frozen=True)
class AirReading:
    timestamp: datetime
    source: str
    station_id: str
    station_name: str
    lat: float
    lon: float
    district: str
    pollutant: str
    concentration: float
    aqi: float | None = None
    quality_flag: str = "ok"

    def to_dict(self) -> dict[str, Any]:
        data = asdict(self)
        data["timestamp"] = isoformat(self.timestamp)
        return data


@dataclass(frozen=True)
class WeatherHour:
    timestamp: datetime
    hour_offset: int
    wind_speed_mps: float
    wind_dir_deg: float
    temp_c: float
    humidity: float
    precipitation_mm: float = 0.0
    boundary_layer_height_m: float | None = None
    wind_speed_850hpa_mps: float = 0.0
    wind_dir_850hpa_deg: float = 0.0

    def to_dict(self) -> dict[str, Any]:
        data = asdict(self)
        data["timestamp"] = isoformat(self.timestamp)
        return data


@dataclass(frozen=True)
class AirQualityForecast:
    district_id: str
    district_name: str
    timestamp: datetime
    hour_offset: int
    pm25: float
    no2: float
    pm10: float | None = None
    aerosol_optical_depth: float | None = None
    source: str = "Open-Meteo"
    quality_flag: str = "forecast_background"

    def to_dict(self) -> dict[str, Any]:
        data = asdict(self)
        data["timestamp"] = isoformat(self.timestamp)
        return data


@dataclass(frozen=True)
class SourceEmission:
    source_id: str
    name: str
    lat: float
    lon: float
    district: str
    height_m: float
    pm25_g_s: float
    no2_g_s: float
    status: str = "active"

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


@dataclass(frozen=True)
class DistrictForecast:
    district_id: str
    district_name: str
    timestamp: datetime
    hour_offset: int
    pm25: float
    no2: float
    aqi: int
    category: str
    wind_speed_mps: float
    wind_dir_deg: float
    wind_u: float
    wind_v: float
    plume_pm25: float
    traffic_index: float
    uncertainty_low: int
    uncertainty_high: int
    health_text: str

    def to_dict(self) -> dict[str, Any]:
        data = asdict(self)
        data["timestamp"] = isoformat(self.timestamp)
        return data


@dataclass(frozen=True)
class Alert:
    district_id: str
    district_name: str
    timestamp: datetime
    pollutant: str
    value: float
    threshold: float
    severity: str
    message: str

    def to_dict(self) -> dict[str, Any]:
        data = asdict(self)
        data["timestamp"] = isoformat(self.timestamp)
        return data


@dataclass(frozen=True)
class FireDetection:
    """FIRMS VIIRS/MODIS fire hotspot with hex grid index and risk score."""

    fire_id: str
    timestamp: datetime
    lat: float
    lon: float
    frp: float
    confidence: str
    satellite: str
    distance_to_hanoi_km: float
    bearing_from_hanoi_deg: float
    h3_index: str = ""
    risk_score: float = 0.0

    def to_dict(self) -> dict[str, Any]:
        data = asdict(self)
        data["timestamp"] = isoformat(self.timestamp)
        return data


@dataclass(frozen=True)
class FireHistoryRecord:
    """Historical fire event used for hit rate calculation."""

    fire_id: str
    h3_index: str
    timestamp: datetime
    frp: float
    wind_850_speed_mps: float
    wind_850_dir_deg: float
    humidity: float
    hanoi_aqi_24h_later: float
    caused_pollution: bool

    def to_dict(self) -> dict[str, Any]:
        data = asdict(self)
        data["timestamp"] = isoformat(self.timestamp)
        return data
