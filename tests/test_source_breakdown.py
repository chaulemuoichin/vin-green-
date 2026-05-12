"""Source attribution math — shares must sum to 1 and respond to inputs."""

from __future__ import annotations

import pytest

from hanoi_air.source_breakdown import (
    HANOI_INVENTORY_ANCHOR,
    attribute_pm25,
    dominant_source,
)


def _approx_sum_one(shares: dict[str, float]) -> None:
    assert sum(shares.values()) == pytest.approx(1.0, abs=1e-3)


def test_shares_sum_to_one_in_typical_case() -> None:
    shares = attribute_pm25(
        pm25_total=42.0,
        traffic_pm25=18.0,
        plume_pm25=4.0,
        seasonal_factor=1.05,
        fire_score=0.0,
    )
    _approx_sum_one(shares)
    assert set(shares.keys()) == {"traffic", "industry", "agriculture", "fire", "other"}


def test_high_plume_hour_increases_industry_share() -> None:
    low_plume = attribute_pm25(
        pm25_total=40.0, traffic_pm25=15.0, plume_pm25=1.0,
        seasonal_factor=1.0, fire_score=0.0,
    )
    high_plume = attribute_pm25(
        pm25_total=40.0, traffic_pm25=15.0, plume_pm25=18.0,
        seasonal_factor=1.0, fire_score=0.0,
    )
    assert high_plume["industry"] > low_plume["industry"]
    _approx_sum_one(low_plume)
    _approx_sum_one(high_plume)


def test_low_traffic_hour_reduces_traffic_share() -> None:
    rush_hour = attribute_pm25(
        pm25_total=55.0, traffic_pm25=22.0, plume_pm25=5.0,
        seasonal_factor=1.0,
    )
    midday = attribute_pm25(
        pm25_total=35.0, traffic_pm25=6.0, plume_pm25=5.0,
        seasonal_factor=1.0,
    )
    assert rush_hour["traffic"] > midday["traffic"]


def test_winter_seasonal_factor_lifts_agriculture_share() -> None:
    summer = attribute_pm25(
        pm25_total=40.0, traffic_pm25=12.0, plume_pm25=4.0,
        seasonal_factor=0.94,
    )
    winter = attribute_pm25(
        pm25_total=40.0, traffic_pm25=12.0, plume_pm25=4.0,
        seasonal_factor=1.18,
    )
    # Winter must lift the agriculture slice meaningfully (≥3 pp) on top of
    # the inventory anchor baseline.
    assert winter["agriculture"] - summer["agriculture"] >= 0.03


def test_fire_score_drives_fire_share() -> None:
    no_fire = attribute_pm25(40.0, 12.0, 4.0, 1.0, fire_score=0.0)
    big_fire = attribute_pm25(40.0, 12.0, 4.0, 1.0, fire_score=0.8)
    # An active fire (score 0.8) must lift the fire slice ≥10 pp above
    # the inventory baseline.
    assert big_fire["fire"] - no_fire["fire"] >= 0.10


def test_zero_total_falls_back_to_inventory_anchor() -> None:
    shares = attribute_pm25(0.0, 0.0, 0.0, 1.0, 0.0)
    assert shares == HANOI_INVENTORY_ANCHOR


def test_dominant_source_returns_highest_key() -> None:
    shares = attribute_pm25(60.0, 32.0, 2.0, 1.0)
    assert dominant_source(shares) == "traffic"
    industrial = attribute_pm25(60.0, 4.0, 30.0, 1.0)
    assert dominant_source(industrial) == "industry"


def test_negative_inputs_are_floored_at_zero() -> None:
    """Negative raw inputs must not produce negative shares; with no live
    signal the inventory anchor still allocates the residual mass."""
    shares = attribute_pm25(
        pm25_total=40.0,
        traffic_pm25=-5.0,
        plume_pm25=-1.0,
        seasonal_factor=0.8,
        fire_score=-0.2,
    )
    _approx_sum_one(shares)
    assert all(v >= 0.0 for v in shares.values())
    # No live signal → traffic share is the anchor proportion of the residual
    no_signal = attribute_pm25(40.0, 0.0, 0.0, 1.0, 0.0)
    assert shares == no_signal


def test_inventory_anchor_distributes_residual_mass() -> None:
    """When no live signals are present, the residual after the background
    floor is distributed by the Hanoi inventory weights."""
    shares = attribute_pm25(40.0, 0.0, 0.0, 1.0, 0.0)
    _approx_sum_one(shares)
    # Background floor is 15 %
    assert shares["other"] == pytest.approx(0.15, abs=1e-3)
    # Residual 85 % is split by inventory anchor (56/20/15/9)
    assert shares["traffic"] == pytest.approx(0.85 * 0.56, abs=1e-3)
    assert shares["industry"] == pytest.approx(0.85 * 0.20, abs=1e-3)
    assert shares["agriculture"] == pytest.approx(0.85 * 0.15, abs=1e-3)
    assert shares["fire"] == pytest.approx(0.85 * 0.09, abs=1e-3)
