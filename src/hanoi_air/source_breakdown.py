"""Per (district × hour) PM2.5 source attribution.

The forecast pipeline already computes every input we need (traffic
contribution, Gaussian plume contribution, seasonal factor). This module
turns them into a normalized share dict suitable for a pie chart.

Inventory anchors come from the Hanoi PM2.5 emission inventory studies
(transport ~56 %, industry ~20 %, agriculture/biomass burning ~15 %,
long-range transport including fire ~9 %). The anchors are used only as
a fallback when the live inputs collapse to zero (e.g. sample mode with
no plume and no traffic); otherwise the shares are *derived from actual
modelled contributions* so calm-wind or low-traffic hours correctly
reweight the pie.
"""

from __future__ import annotations

HANOI_INVENTORY_ANCHOR: dict[str, float] = {
    "traffic": 0.56,
    "industry": 0.20,
    "agriculture": 0.15,
    "fire": 0.09,
    "other": 0.00,
}

# Floor share of PM2.5 always attributed to long-range transport / unmodelled
# background. Hanoi receives a meaningful regional baseline (ESCAP HAQ study
# attributes ~15 % to long-range transport in winter), and reserving this slice
# prevents the inventory blend from over-claiming local accountability.
BACKGROUND_FLOOR_SHARE: float = 0.15


def attribute_pm25(
    pm25_total: float,
    traffic_pm25: float,
    plume_pm25: float,
    seasonal_factor: float,
    fire_score: float = 0.0,
) -> dict[str, float]:
    """Return PM2.5 source shares that sum to 1.0.

    Parameters mirror the variables computed inside
    :func:`hanoi_air.forecast.build_forecast`:

    - ``pm25_total`` — final clamped PM2.5 for the (district, hour) cell.
    - ``traffic_pm25`` — traffic contribution already in µg/m³.
    - ``plume_pm25`` — Gaussian plume contribution already weighted by
      the 0.46 factor used in the pipeline.
    - ``seasonal_factor`` — 1.0 baseline, >1 in winter shoulder months
      where straw / biomass burning ramps up.
    - ``fire_score`` — 0–1 fire risk from :mod:`fire_risk`. Defaults to
      0; Day 4 wires the real value in.
    """
    pm25_total_f = max(0.0, float(pm25_total))
    raw_traffic = max(0.0, float(traffic_pm25))
    raw_industry = max(0.0, float(plume_pm25))
    raw_fire = max(0.0, float(fire_score)) * 8.0
    raw_agriculture = max(0.0, float(seasonal_factor) - 1.0) * pm25_total_f * 0.6

    explained = raw_traffic + raw_industry + raw_fire + raw_agriculture

    if pm25_total_f <= 0:
        return dict(HANOI_INVENTORY_ANCHOR)

    # The heuristic's PM2.5 obs+background blend embeds traffic/industry/ag
    # signals that the pipeline doesn't expose separately. We reserve a floor
    # for genuine background, then redistribute the remainder per the Hanoi
    # inventory anchor so the pie reflects sectoral reality. Live signals
    # (traffic_pm25, plume_pm25, fire_score) add on top, so high-plume hours
    # still tilt the pie toward industry.
    background_mass = BACKGROUND_FLOOR_SHARE * pm25_total_f
    residual = max(0.0, pm25_total_f - explained - background_mass)

    contributions = {
        "traffic": raw_traffic + residual * HANOI_INVENTORY_ANCHOR["traffic"],
        "industry": raw_industry + residual * HANOI_INVENTORY_ANCHOR["industry"],
        "agriculture": raw_agriculture + residual * HANOI_INVENTORY_ANCHOR["agriculture"],
        "fire": raw_fire + residual * HANOI_INVENTORY_ANCHOR["fire"],
        "other": background_mass,
    }

    total = sum(contributions.values())
    if total <= 0:
        return dict(HANOI_INVENTORY_ANCHOR)

    shares = {key: value / total for key, value in contributions.items()}
    return _normalize(shares)


def _normalize(shares: dict[str, float]) -> dict[str, float]:
    """Round to 4 decimals and ensure the values sum to exactly 1.0."""
    rounded = {key: round(value, 4) for key, value in shares.items()}
    drift = round(1.0 - sum(rounded.values()), 4)
    if abs(drift) >= 1e-4:
        largest_key = max(rounded, key=lambda k: rounded[k])
        rounded[largest_key] = round(rounded[largest_key] + drift, 4)
    return rounded


def dominant_source(shares: dict[str, float]) -> str:
    """Return the source label with the highest share."""
    if not shares:
        return "other"
    return max(shares, key=lambda k: shares.get(k, 0.0))
