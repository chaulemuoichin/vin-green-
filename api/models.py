"""API response models and schemas."""

from __future__ import annotations

from datetime import datetime
from typing import Any

from pydantic import BaseModel, Field


class HealthResponse(BaseModel):
    """Health check response."""

    status: str = Field(..., description="Health status")
    service: str = Field(..., description="Service name")
    timestamp: datetime | None = Field(None, description="Response timestamp")


class District(BaseModel):
    """District information."""

    id: str = Field(..., description="District ID (slug)")
    name_vi: str = Field(..., description="Vietnamese district name")
    name_en: str = Field(..., description="English district name")
    latitude: float = Field(..., description="District centroid latitude")
    longitude: float = Field(..., description="District centroid longitude")


class DistrictsResponse(BaseModel):
    """Districts list response."""

    districts: list[District] = Field(..., description="List of districts")
    count: int = Field(..., description="Total number of districts")


class Forecast(BaseModel):
    """Single forecast record."""

    district_id: str = Field(..., description="District ID")
    hour_offset: int = Field(..., description="Hour offset from now (0-23)")
    pm25: float = Field(..., description="PM2.5 forecast (µg/m³)")
    no2: float = Field(..., description="NO₂ forecast (ppb)")
    aqi: float = Field(..., description="Air Quality Index")
    aqi_category: str = Field(..., description="AQI category (Good, Moderate, etc.)")
    wind_direction: str = Field(..., description="Wind direction (N, NE, E, etc.)")
    wind_speed: float = Field(..., description="Wind speed (m/s)")
    temperature: float = Field(..., description="Temperature (°C)")
    humidity: float = Field(..., description="Relative humidity (%)")
    confidence: float = Field(..., description="Forecast confidence/uncertainty (µg/m³)")


class ForecastResponse(BaseModel):
    """Forecast response with metadata."""

    forecasts: list[Forecast] = Field(..., description="List of forecasts")
    generated_at: datetime = Field(..., description="Forecast generation time (UTC)")
    data_sources: list[str] = Field(..., description="Data sources used")
    alerts: list[dict] = Field(default_factory=list, description="Active alerts")


class Alert(BaseModel):
    """Air quality alert."""

    id: str = Field(..., description="Alert ID")
    district_id: str = Field(..., description="Affected district")
    alert_type: str = Field(..., description="Alert type (high_pm25, high_no2, etc.)")
    severity: str = Field(..., description="Severity (warning, critical)")
    message: str = Field(..., description="Alert message")
    triggered_at: datetime = Field(..., description="Alert trigger time (UTC)")
    expires_at: datetime = Field(..., description="Alert expiration time (UTC)")


class AlertsResponse(BaseModel):
    """Alerts response."""

    alerts: list[Alert] = Field(..., description="List of active alerts")
    generated_at: datetime = Field(..., description="Response generation time (UTC)")


class SourceStatus(BaseModel):
    """Data source health status."""

    name: str = Field(..., description="Source name")
    status: str = Field(..., description="Status (ok, stale, error, circuit_open)")
    last_success_at: datetime | None = Field(None, description="Last successful fetch (UTC)")
    last_error: str | None = Field(None, description="Last error message")
    record_count: int = Field(0, description="Records from this source")
    is_stale: bool = Field(..., description="Is data stale?")
    cadence_minutes: int = Field(..., description="Expected update frequency (minutes)")


class SourcesResponse(BaseModel):
    """Data sources status response."""

    sources: list[SourceStatus] = Field(..., description="List of data sources")
    generated_at: datetime = Field(..., description="Response generation time (UTC)")


class ErrorResponse(BaseModel):
    """Error response."""

    detail: str = Field(..., description="Error message")
    type: str = Field(..., description="Error type")
    timestamp: datetime = Field(..., description="Error time (UTC)")


class RateLimitError(BaseModel):
    """Rate limit error response."""

    detail: str = Field(..., description="Rate limit message")
    retry_after: int = Field(..., description="Seconds to wait before retry")
