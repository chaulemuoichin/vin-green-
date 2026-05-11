from __future__ import annotations

import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

from fastapi import FastAPI, Query

from hanoi_air.config import get_settings
from hanoi_air.forecast import build_cached_forecast
from hanoi_air.geography import load_districts
from hanoi_air.observability import init_sentry

init_sentry(service="api")

app = FastAPI(title="Hanoi Air Forecast API", version="0.2.0")


@app.get("/health")
def health() -> dict:
    return {"status": "ok", "service": "hanoi-air-forecast"}


@app.get("/districts")
def districts() -> dict:
    return {"districts": [district.to_dict() for district in load_districts()]}


@app.get("/forecast")
def forecast(
    district_id: str | None = None,
    hour_offset: int | None = Query(default=None, ge=0, le=23),
    force_refresh: bool = False,
    use_live: bool = True,
) -> dict:
    bundle = build_cached_forecast(get_settings(), force_refresh=force_refresh, use_live=use_live)
    rows = bundle["forecasts"]
    if district_id:
        rows = [row for row in rows if row["district_id"] == district_id]
    if hour_offset is not None:
        rows = [row for row in rows if int(row["hour_offset"]) == hour_offset]
    return {**bundle, "forecasts": rows}


@app.get("/alerts")
def alerts(force_refresh: bool = False, use_live: bool = True) -> dict:
    bundle = build_cached_forecast(get_settings(), force_refresh=force_refresh, use_live=use_live)
    return {"alerts": bundle["alerts"], "generated_at": bundle["generated_at"]}
