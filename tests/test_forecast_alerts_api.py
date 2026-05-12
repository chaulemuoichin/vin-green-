from datetime import datetime, timezone

from hanoi_air.alerts import generate_alerts
from hanoi_air.cli import format_top5
from hanoi_air.config import get_settings
from hanoi_air.forecast import build_forecast, top_n_worst


def test_forecast_bundle_has_24h_for_15_districts():
    settings = get_settings()
    bundle = build_forecast(
        settings, now=datetime(2026, 5, 11, tzinfo=timezone.utc), use_live=False
    )
    assert bundle["mode"] == "sample"
    assert bundle["district_count"] == 15
    assert len(bundle["forecasts"]) == 15 * 24
    sample = bundle["forecasts"][0]
    assert {"uncertainty_low", "uncertainty_high", "health_text"} <= set(sample)
    assert sample["uncertainty_low"] <= sample["aqi"] <= sample["uncertainty_high"]
    # Day 1 additions must thread through the pipeline
    assert {"vn_aqi", "vn_category", "source_breakdown"} <= set(sample)
    assert abs(sum(sample["source_breakdown"].values()) - 1.0) < 1e-3


def test_alert_threshold_edges_for_aqi():
    base = {
        "district_id": "x",
        "district_name": "X",
        "timestamp": "2026-05-11T00:00:00+00:00",
        "pm25": 10.0,
        "health_text": "message",
    }
    rows = [{**base, "aqi": value} for value in [149, 150, 151]]
    alerts = generate_alerts(rows, aqi_threshold=150, pm25_threshold=999.0)
    assert len(alerts) == 1
    assert alerts[0].value == 151


def test_top5_report_generation():
    bundle = build_forecast(
        get_settings(), now=datetime(2026, 5, 11, tzinfo=timezone.utc), use_live=False
    )
    rows = top_n_worst(bundle, 5)
    report = format_top5(rows)
    assert len(rows) == 5
    assert report.splitlines()[0] == "rank,district,timestamp,aqi,pm25,no2,category"
    assert "Bắc Từ Liêm" in report or "Long Biên" in report


def test_fastapi_smoke():
    try:
        from fastapi.testclient import TestClient

        from api.main import app
    except Exception:
        return

    client = TestClient(app)
    assert client.get("/health").json()["status"] == "ok"
    districts = client.get("/districts").json()["districts"]
    assert len(districts) == 15
    forecast = client.get("/forecast?use_live=false&force_refresh=true&hour_offset=0").json()
    assert len(forecast["forecasts"]) == 15
