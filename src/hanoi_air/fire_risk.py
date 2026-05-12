"""Per-district fire risk from regional biomass burning hotspots.

The eventual implementation aggregates NASA FIRMS VIIRS hits over an H3
res-7 hex grid, scoring each cell by (hit_rate × FRP_sigmoid ×
distance_decay × upwind_alignment) and projecting plume arrival hours
from the 850 hPa wind. For Week 1 this module exposes the data shape
and a deterministic stub aggregator so the rest of the pipeline can
consume fire risk uniformly. When real FIRMS ingestion lands, only the
``aggregate_fires_to_districts`` body needs to change.
"""

from __future__ import annotations

import math
from collections.abc import Iterable
from dataclasses import asdict, dataclass
from typing import Any

from .geography import haversine_km
from .schemas import District


@dataclass(frozen=True)
class FireDetection:
    """One FIRMS hotspot detection."""
    lat: float
    lon: float
    frp_mw: float       # Fire Radiative Power
    confidence: str     # "n" / "l" / "h" (nominal / low / high)
    origin: str = "Unknown"  # "Laos", "Vietnam", "Myanmar", "Thailand", ...

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


@dataclass(frozen=True)
class FireRisk:
    """Per-district aggregated fire impact projection."""
    district_id: str
    district_name: str
    risk: float          # 0..1 combined score
    arrival_h: float     # hours until plume arrives (great-circle / wind speed)
    pm25_delta: float    # expected µg/m³ bump at peak
    origin: str          # dominant source country
    detection_count: int

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


def _frp_sigmoid(frp_mw: float, half: float = 100.0) -> float:
    return 1.0 / (1.0 + math.exp(-(frp_mw - half) / max(1.0, half * 0.3)))


def _distance_decay(distance_km: float, half_km: float = 300.0) -> float:
    return math.exp(-math.log(2.0) * distance_km / max(1.0, half_km))


def _upwind_alignment(
    fire_lat: float,
    fire_lon: float,
    district_lat: float,
    district_lon: float,
    wind_dir_deg_850: float,
    half_angle_deg: float = 45.0,
) -> float:
    """1.0 when the district is directly downwind of the fire at 850 hPa."""
    # Lazy import to avoid a circular dependency.
    from .downwind import _angle_diff_deg, bearing_deg

    downwind_to = (wind_dir_deg_850 + 180.0) % 360.0
    bearing = bearing_deg(fire_lat, fire_lon, district_lat, district_lon)
    angle_off = _angle_diff_deg(bearing, downwind_to)
    if angle_off > half_angle_deg:
        return 0.0
    return math.cos(math.radians(angle_off))


def aggregate_fires_to_districts(
    fires: Iterable[FireDetection],
    districts: Iterable[District],
    wind_dir_deg_850: float,
    wind_speed_mps_850: float,
) -> list[FireRisk]:
    """Score every district against every fire and return non-trivial risks."""
    fires_list = list(fires)
    if not fires_list:
        return []
    out: list[FireRisk] = []
    for district in districts:
        score = 0.0
        weighted_delta = 0.0
        weighted_arrival = 0.0
        weight_total = 0.0
        count = 0
        dominant_origin = "Unknown"
        best_origin_weight = 0.0
        for fire in fires_list:
            dist = haversine_km(fire.lat, fire.lon, district.lat, district.lon)
            if dist > 600.0:
                continue
            frp = _frp_sigmoid(fire.frp_mw)
            decay = _distance_decay(dist)
            align = _upwind_alignment(
                fire.lat, fire.lon, district.lat, district.lon, wind_dir_deg_850
            )
            confidence_weight = {"h": 1.0, "n": 0.85, "l": 0.55}.get(fire.confidence, 0.7)
            cell_score = frp * decay * align * confidence_weight
            if cell_score <= 0:
                continue
            count += 1
            score = max(score, cell_score)
            # Arrival in hours = great-circle distance / wind speed (m/s → km/h).
            speed_kmh = max(0.5, wind_speed_mps_850 * 3.6)
            arrival_h = dist / speed_kmh
            weighted_arrival += arrival_h * cell_score
            # 18 µg/m³ peak bump from a fully aligned high-FRP fire.
            weighted_delta += 18.0 * cell_score
            weight_total += cell_score
            if cell_score > best_origin_weight:
                best_origin_weight = cell_score
                dominant_origin = fire.origin
        if score <= 0:
            continue
        out.append(FireRisk(
            district_id=district.district_id,
            district_name=district.name,
            risk=round(min(1.0, score), 4),
            arrival_h=round(weighted_arrival / weight_total, 1),
            pm25_delta=round(weighted_delta / weight_total, 1),
            origin=dominant_origin,
            detection_count=count,
        ))
    return out


def fire_score_by_district(fire_risks: Iterable[FireRisk]) -> dict[str, float]:
    """Flatten to a ``{district_id: score}`` map for ``source_breakdown``."""
    return {fr.district_id: fr.risk for fr in fire_risks}
