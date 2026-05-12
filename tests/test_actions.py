"""Citizen + government recommendation rules."""

from __future__ import annotations

from hanoi_air.actions import (
    citizen_actions,
    government_actions,
    recommendations,
)


def _row(**overrides):
    base = {
        "aqi": 80,
        "pm25": 30.0,
        "hour_offset": 12,
        "district_name": "Hoàn Kiếm",
        "source_breakdown": {
            "traffic": 0.4, "industry": 0.2, "agriculture": 0.15,
            "fire": 0.05, "other": 0.20,
        },
        "timestamp": "2026-05-12T05:00:00+00:00",  # 12:00 Hanoi local
    }
    base.update(overrides)
    return base


def test_good_air_recommends_no_action_to_citizens() -> None:
    out = citizen_actions(_row(aqi=40, pm25=10))
    joined = " ".join(out)
    assert "tốt" in joined.lower() or "bình thường" in joined.lower()
    assert not any("N95" in item or "n95" in item for item in out)


def test_unhealthy_air_recommends_n95_at_rush_hour() -> None:
    out = citizen_actions(_row(
        aqi=170, pm25=90,
        # 08:00 Hanoi local = 01:00 UTC
        timestamp="2026-05-12T01:00:00+00:00",
    ))
    text = " ".join(out)
    assert "N95" in text or "KF94" in text
    assert "cao điểm" in text or "xe buýt" in text


def test_government_quiet_on_good_air() -> None:
    out = government_actions(_row(aqi=50), downwind_risk=0.0)
    assert out == []


def test_government_traffic_action_when_traffic_dominant() -> None:
    out = government_actions(_row(
        aqi=170,
        source_breakdown={"traffic": 0.55, "industry": 0.10, "agriculture": 0.10,
                          "fire": 0.05, "other": 0.20},
        timestamp="2026-05-12T01:00:00+00:00",  # 08:00 Hanoi
    ), downwind_risk=0.1)
    joined = " ".join(out)
    assert "xe tải" in joined.lower() or "xe cá nhân" in joined.lower()


def test_government_industry_action_requires_downwind_and_industry_share() -> None:
    payload = _row(
        aqi=180,
        source_breakdown={"traffic": 0.20, "industry": 0.30, "agriculture": 0.10,
                          "fire": 0.05, "other": 0.35},
    )
    # Without downwind alignment → no industry action
    without_downwind = government_actions(payload, downwind_risk=0.05)
    assert not any("nhà máy" in s for s in without_downwind)
    # With strong downwind → industry action lights up
    with_downwind = government_actions(payload, downwind_risk=0.6)
    assert any("nhà máy" in s for s in with_downwind)


def test_government_school_action_above_aqi_200() -> None:
    out = government_actions(_row(aqi=220), downwind_risk=0.0)
    assert any("trường học" in s for s in out)


def test_government_emergency_above_aqi_250() -> None:
    out = government_actions(_row(aqi=260), downwind_risk=0.0)
    assert any("khẩn cấp" in s.lower() for s in out)


def test_recommendations_wraps_both_lists() -> None:
    bundle = recommendations(_row(aqi=170), downwind_risk=0.5)
    assert "citizen" in bundle
    assert "government" in bundle
    assert isinstance(bundle["citizen"], list)
    assert isinstance(bundle["government"], list)


def test_citizen_industry_hint_when_dominant_and_unhealthy() -> None:
    out = citizen_actions(_row(
        aqi=160, pm25=80,
        source_breakdown={"traffic": 0.10, "industry": 0.40, "agriculture": 0.10,
                          "fire": 0.05, "other": 0.35},
    ))
    assert any("nhà máy" in s for s in out)
