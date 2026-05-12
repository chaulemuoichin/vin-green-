"""Application settings loaded from environment + .env, validated via pydantic.

Callers should obtain settings through :func:`get_settings`; the result is
cached per-process so reads are cheap. To override in tests, construct a
``Settings(**overrides)`` directly and pass it to functions that accept it.

Secret-bearing fields are declared with ``repr=False`` so they never appear
in ``repr(settings)`` or default logging output, while still being plain
strings at call sites (preserves backwards-compat with the dataclass version).
"""

from __future__ import annotations

from functools import lru_cache
from pathlib import Path
from typing import Literal

from pydantic import Field, field_validator
from pydantic_settings import BaseSettings, SettingsConfigDict

PROJECT_ROOT = Path(__file__).resolve().parents[2]

HANOI_BOUNDS = {
    "south": 20.50,
    "west": 105.25,
    "north": 21.45,
    "east": 106.15,
}


class Settings(BaseSettings):
    """Runtime configuration. See ``.env.example`` for the full list of keys."""

    model_config = SettingsConfigDict(
        env_file=PROJECT_ROOT / ".env",
        env_file_encoding="utf-8",
        extra="ignore",
        case_sensitive=False,
    )

    # ── Filesystem paths (computed, not env-driven) ─────────────────────────
    project_root: Path = Field(default=PROJECT_ROOT, exclude=True)
    data_dir: Path = Field(default=PROJECT_ROOT / "data", exclude=True)
    sample_dir: Path = Field(default=PROJECT_ROOT / "data" / "sample", exclude=True)
    raw_dir: Path = Field(default=PROJECT_ROOT / "data" / "raw", exclude=True)
    processed_dir: Path = Field(default=PROJECT_ROOT / "data" / "processed", exclude=True)
    cache_file: Path = Field(default=PROJECT_ROOT / ".cache" / "forecast_cache.json", exclude=True)
    source_status_file: Path = Field(
        default=PROJECT_ROOT / ".cache" / "source_status.json", exclude=True
    )
    cache_dir: Path = Field(default=PROJECT_ROOT / ".cache", exclude=True)

    # ── External API credentials (hidden from repr to avoid log leakage) ───
    aqicn_token: str | None = Field(default=None, repr=False)
    openaq_api_key: str | None = Field(default=None, repr=False)
    openweather_api_key: str | None = Field(default=None, repr=False)
    google_maps_api_key: str | None = Field(default=None, repr=False)
    cdsapi_url: str | None = None
    cdsapi_key: str | None = Field(default=None, repr=False)
    cems_api_url: str | None = None
    alert_webhook_url: str | None = Field(default=None, repr=False)
    redis_url: str | None = None

    # ── Fire & Satellite (Phase 5 — upwind smoke detection) ──────────────
    firms_map_key: str = Field(
        default="574c47a834cae0aead0af0ab21e2ba6b",
        repr=False,
        description="NASA FIRMS API key"
    )
    gee_project_id: str = Field(
        default="these-streets",
        description="Google Earth Engine project ID"
    )
    cams_api_key: str | None = Field(default=None, repr=False, description="CAMS/Copernicus API key (optional)")

    # ── API security ──────────────────────────────────────────────────────
    api_keys: str | None = Field(default=None, repr=False, description="Comma-separated API keys")
    cors_allowed_origins: str = Field(
        default="http://localhost:8501,http://localhost:8000,http://localhost:3000",
        description="Comma-separated CORS allowed origins",
    )
    forecast_horizon_hours: int = Field(default=24, ge=1, le=72)
    cache_ttl_seconds: int = Field(default=1800, ge=60)
    alert_aqi_threshold: int = Field(default=150, ge=0, le=500)
    alert_pm25_threshold: float = Field(default=55.5, ge=0.0)

    # ── Feature flags ─────────────────────────────────────────────────────
    use_live_data: bool = True
    enable_public_crawl: bool = True
    enable_overpass: bool = False
    somo_site_ids: str = "1,39"

    # ── Logging ───────────────────────────────────────────────────────────
    hanoi_air_log_level: Literal["TRACE", "DEBUG", "INFO", "WARNING", "ERROR", "CRITICAL"] = "INFO"
    hanoi_air_log_json: bool = False

    @field_validator(
        "aqicn_token",
        "openaq_api_key",
        "openweather_api_key",
        "google_maps_api_key",
        "cdsapi_url",
        "cdsapi_key",
        "cems_api_url",
        "alert_webhook_url",
        "redis_url",
        "firms_map_key",
        "cams_api_key",
        mode="before",
    )
    @classmethod
    def _empty_string_to_none(cls, value: object) -> object:
        """Treat empty strings ("") from .env as missing."""
        if isinstance(value, str) and not value.strip():
            return None
        if isinstance(value, str):
            return value.strip()
        return value

    @field_validator("somo_site_ids")
    @classmethod
    def _validate_site_ids(cls, value: str) -> str:
        cleaned = ",".join(item.strip() for item in value.split(",") if item.strip())
        return cleaned or "1"

    # Legacy compatibility ---------------------------------------------------
    @classmethod
    def from_env(cls) -> Settings:
        """Backwards-compat shim for old call sites."""
        return cls()


@lru_cache(maxsize=1)
def get_settings() -> Settings:
    """Cached settings instance for normal application use."""
    return Settings()


def reload_settings() -> Settings:
    """Drop the cached settings and reload from env. Use only in tests."""
    get_settings.cache_clear()
    return get_settings()
