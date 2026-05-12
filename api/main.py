"""Hanoi Air Forecast API.

Auth: ``X-API-Key`` header verified against ``settings.api_keys`` (CSV).
When ``API_KEYS`` is unset, every request is allowed (development mode).
``/health`` and ``/districts`` are always public.

Rate limits: slowapi, configurable via ``RATE_LIMIT_FORECAST`` and
``RATE_LIMIT_ALERTS`` env vars (slowapi format, default "60/minute" and
"30/minute").
"""

from __future__ import annotations

import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

from fastapi import Depends, FastAPI, Query, Request
from fastapi.responses import JSONResponse
from slowapi import Limiter
from slowapi.errors import RateLimitExceeded
from slowapi.middleware import SlowAPIMiddleware

from api.auth import get_api_key_for_rate_limit, verify_api_key, verify_api_key_only
from api.jwt_auth import issue_token
from api.middleware import setup_cors_middleware
from hanoi_air.config import get_settings
from hanoi_air.forecast import build_cached_forecast
from hanoi_air.geography import load_districts
from hanoi_air.observability import init_sentry

init_sentry(service="api")

_settings = get_settings()

limiter = Limiter(key_func=get_api_key_for_rate_limit, default_limits=[])

app = FastAPI(
    title="Hanoi Air Forecast API",
    version="0.3.0",
    description=(
        "PM2.5 / NO₂ / AQI 24-hour forecast for 15 Hanoi districts, plus "
        "downwind risk, source attribution, citizen/government actions, and "
        "fire alerts. Authenticate with the `X-API-Key` header."
    ),
)
app.state.limiter = limiter
app.add_middleware(SlowAPIMiddleware)
setup_cors_middleware(app)


@app.exception_handler(RateLimitExceeded)
async def _rate_limit_handler(request: Request, exc: RateLimitExceeded) -> JSONResponse:
    return JSONResponse(
        status_code=429,
        content={
            "detail": f"Rate limit exceeded: {exc.detail}",
            "type": "rate_limit_exceeded",
        },
        headers={"Retry-After": "60"},
    )


@app.get("/health", tags=["meta"])
def health() -> dict:
    return {"status": "ok", "service": "hanoi-air-forecast"}


@app.get("/districts", tags=["meta"])
def districts() -> dict:
    return {"districts": [district.to_dict() for district in load_districts()]}


@app.post("/auth/token", tags=["auth"])
def auth_token(
    api_key: str = Depends(verify_api_key_only),
) -> dict:
    """Mint a short-lived HS256 JWT for the supplied X-API-Key.

    Returns 503 if `JWT_SECRET` is not configured. The X-API-Key flow
    remains available regardless — JWT is additive, not a replacement.
    """
    return issue_token(api_key)


def _filter_row(row: dict, fields: set[str] | None) -> dict:
    if not fields:
        return row
    minimal = {"district_id", "district_name", "hour_offset", "timestamp",
               "pm25", "aqi", "category"}
    keep = minimal | fields
    return {key: value for key, value in row.items() if key in keep}


@app.get("/forecast", tags=["forecast"])
@limiter.limit(_settings.rate_limit_forecast)
def forecast(
    request: Request,
    district: str | None = Query(
        default=None,
        description="District slug (e.g. `hoan_kiem`). Filters rows to this district.",
    ),
    hours: int | None = Query(
        default=None, ge=1, le=24,
        description="Return only the next `hours` hour-offsets (0 .. hours-1).",
    ),
    district_id: str | None = Query(
        default=None,
        description="Deprecated — same as `district`. Kept for backwards compatibility.",
    ),
    hour_offset: int | None = Query(
        default=None, ge=0, le=23,
        description="Return only this exact hour offset. Wins over `hours`.",
    ),
    fields: str | None = Query(
        default=None,
        description="Comma-separated field allowlist to trim heavy rows "
                    "(e.g. `vn_aqi,source_breakdown,actions,downwind_risk`).",
    ),
    force_refresh: bool = False,
    use_live: bool = True,
    _api_key: str = Depends(verify_api_key),
) -> dict:
    bundle = build_cached_forecast(get_settings(), force_refresh=force_refresh, use_live=use_live)
    rows = bundle["forecasts"]
    target = district or district_id
    if target:
        rows = [row for row in rows if row["district_id"] == target]
    if hour_offset is not None:
        rows = [row for row in rows if int(row["hour_offset"]) == hour_offset]
    elif hours is not None:
        rows = [row for row in rows if int(row["hour_offset"]) < hours]
    field_set = (
        {f.strip() for f in fields.split(",") if f.strip()} if fields else None
    )
    if field_set:
        rows = [_filter_row(row, field_set) for row in rows]
    return {**bundle, "forecasts": rows}


@app.get("/alerts", tags=["forecast"])
@limiter.limit(_settings.rate_limit_alerts)
def alerts(
    request: Request,
    force_refresh: bool = False,
    use_live: bool = True,
    _api_key: str = Depends(verify_api_key),
) -> dict:
    bundle = build_cached_forecast(get_settings(), force_refresh=force_refresh, use_live=use_live)
    return {"alerts": bundle["alerts"], "generated_at": bundle["generated_at"]}
