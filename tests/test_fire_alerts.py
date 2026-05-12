"""Fire risk → Alert pipeline."""

from __future__ import annotations

from datetime import datetime, timezone

from hanoi_air.fire_alerts import fire_alert_messages
from hanoi_air.fire_risk import (
    FireDetection,
    FireRisk,
    aggregate_fires_to_districts,
)
from hanoi_air.schemas import District


def _district(district_id: str, lat: float, lon: float) -> District:
    return District(district_id=district_id, name=district_id.replace("_", " ").title(),
                    lat=lat, lon=lon)


def test_no_fires_returns_no_risks() -> None:
    risks = aggregate_fires_to_districts(
        fires=[], districts=[_district("hoan_kiem", 21.03, 105.85)],
        wind_dir_deg_850=90.0, wind_speed_mps_850=10.0,
    )
    assert risks == []


def test_downwind_fire_produces_district_risk() -> None:
    # Fire to the west of Hanoi at 200 km, wind FROM west blowing east
    fire = FireDetection(lat=21.0, lon=103.5, frp_mw=180.0,
                         confidence="h", origin="Laos")
    risks = aggregate_fires_to_districts(
        fires=[fire],
        districts=[_district("hoan_kiem", 21.03, 105.85)],
        wind_dir_deg_850=270.0, wind_speed_mps_850=10.0,
    )
    assert len(risks) == 1
    fr = risks[0]
    assert fr.district_id == "hoan_kiem"
    assert fr.risk > 0
    assert fr.arrival_h > 0
    assert fr.origin == "Laos"


def test_upwind_fire_is_filtered_out() -> None:
    # Fire to the east, wind FROM west — fire is upwind, no risk
    fire = FireDetection(lat=21.0, lon=108.0, frp_mw=200.0,
                         confidence="h", origin="China")
    risks = aggregate_fires_to_districts(
        fires=[fire], districts=[_district("hoan_kiem", 21.03, 105.85)],
        wind_dir_deg_850=270.0, wind_speed_mps_850=10.0,
    )
    assert risks == []


def test_far_fire_is_filtered_out() -> None:
    # Fire 700 km away — beyond the 600 km cap
    fire = FireDetection(lat=21.0, lon=98.0, frp_mw=200.0,
                         confidence="h", origin="Myanmar")
    risks = aggregate_fires_to_districts(
        fires=[fire], districts=[_district("hoan_kiem", 21.03, 105.85)],
        wind_dir_deg_850=270.0, wind_speed_mps_850=10.0,
    )
    assert risks == []


def test_fire_alert_message_contains_eta_and_district() -> None:
    fr = FireRisk(
        district_id="hoan_kiem", district_name="Hoàn Kiếm",
        risk=0.5, arrival_h=14.0, pm25_delta=18.0, origin="Laos",
        detection_count=12,
    )
    alerts = fire_alert_messages([fr], now=datetime(2026, 5, 12, tzinfo=timezone.utc))
    assert len(alerts) == 1
    alert = alerts[0]
    assert "14h" in alert.message
    assert "Hoàn Kiếm" in alert.message
    assert "Laos" in alert.message
    assert alert.pollutant == "FIRE_PM25"


def test_fire_alert_threshold_suppresses_low_risk() -> None:
    fr_low = FireRisk(
        district_id="hoan_kiem", district_name="Hoàn Kiếm",
        risk=0.20, arrival_h=14.0, pm25_delta=4.0, origin="Laos",
        detection_count=2,
    )
    assert fire_alert_messages([fr_low], risk_threshold=0.30) == []
    assert len(fire_alert_messages([fr_low], risk_threshold=0.10)) == 1


def test_fire_alert_severity_scales_with_risk() -> None:
    fr_yellow = FireRisk(district_id="a", district_name="A", risk=0.35,
                         arrival_h=10, pm25_delta=8, origin="X", detection_count=1)
    fr_orange = FireRisk(district_id="b", district_name="B", risk=0.55,
                         arrival_h=10, pm25_delta=12, origin="X", detection_count=2)
    fr_red = FireRisk(district_id="c", district_name="C", risk=0.80,
                      arrival_h=10, pm25_delta=20, origin="X", detection_count=5)
    alerts = fire_alert_messages([fr_yellow, fr_orange, fr_red])
    severities = [a.severity for a in alerts]
    assert severities == ["yellow", "orange", "red"]
