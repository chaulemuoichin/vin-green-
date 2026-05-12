"""Downwind risk zones: source → wind bearing → district intersect.

For each emission source and weather hour, we compute a cone-shaped
downwind wedge and the per-district intersection score. The score
combines angular alignment with the wind and distance decay, so a
district directly downwind 10 km from a factory gets near-1.0 while a
district 45° off-axis at 20 km gets near zero.

Math conventions:
    - ``wind_dir_deg`` is meteorological (the direction the wind blows
      FROM). The downwind direction is therefore ``wind_dir_deg + 180``.
    - ``bearing_deg(src → tgt)`` is 0 at north, 90 at east. The smallest
      signed angle between the bearing and the downwind direction
      determines whether the target is in-cone.
"""

from __future__ import annotations

import math
from collections.abc import Iterable

from .geography import haversine_km
from .schemas import District, SourceEmission, WeatherHour
from .weather import offset_latlon

DEFAULT_HALF_ANGLE_DEG: float = 22.5
DEFAULT_WEDGE_LENGTH_KM: float = 20.0
DEFAULT_MAX_DISTANCE_KM: float = 25.0
DEFAULT_DISTANCE_DECAY_KM: float = 12.0


def bearing_deg(src_lat: float, src_lon: float, tgt_lat: float, tgt_lon: float) -> float:
    """Initial bearing from source to target (0 = N, 90 = E)."""
    phi1 = math.radians(src_lat)
    phi2 = math.radians(tgt_lat)
    d_lambda = math.radians(tgt_lon - src_lon)
    y = math.sin(d_lambda) * math.cos(phi2)
    x = math.cos(phi1) * math.sin(phi2) - math.sin(phi1) * math.cos(phi2) * math.cos(d_lambda)
    return (math.degrees(math.atan2(y, x)) + 360.0) % 360.0


def _angle_diff_deg(a: float, b: float) -> float:
    """Smallest unsigned difference between two bearings (0 ≤ diff ≤ 180)."""
    diff = abs((a - b + 180.0) % 360.0 - 180.0)
    return diff


def downwind_score(
    source: SourceEmission,
    district: District,
    wind_dir_deg: float,
    wind_speed_mps: float,
    half_angle_deg: float = 45.0,
    max_distance_km: float = DEFAULT_MAX_DISTANCE_KM,
    distance_decay_km: float = DEFAULT_DISTANCE_DECAY_KM,
) -> float:
    """Return 0–1 downwind impact score from source onto district.

    Returns 0 if the district is upwind, outside the cone, or beyond
    ``max_distance_km``. Also returns 0 in calm conditions (< 0.3 m/s)
    where wind direction is meaningless.
    """
    if wind_speed_mps < 0.3:
        return 0.0
    dist_km = haversine_km(source.lat, source.lon, district.lat, district.lon)
    if dist_km > max_distance_km or dist_km <= 0.0:
        return 0.0
    downwind_to = (wind_dir_deg + 180.0) % 360.0
    bearing = bearing_deg(source.lat, source.lon, district.lat, district.lon)
    angle_off = _angle_diff_deg(bearing, downwind_to)
    if angle_off > half_angle_deg:
        return 0.0
    angle_factor = math.cos(math.radians(angle_off))
    distance_factor = math.exp(-dist_km / distance_decay_km)
    return round(angle_factor * distance_factor, 4)


def downwind_polygon(
    source: SourceEmission,
    wind_dir_deg: float,
    wind_speed_mps: float,
    length_km: float = DEFAULT_WEDGE_LENGTH_KM,
    half_angle_deg: float = DEFAULT_HALF_ANGLE_DEG,
    arc_points: int = 5,
) -> list[tuple[float, float]]:
    """Return the (lat, lon) vertices of a downwind wedge polygon.

    The polygon is the cone source → arc, closed back at the source so
    Folium renders it as a filled triangle/wedge. Returns an empty list
    in calm conditions to signal "no plume to draw."
    """
    if wind_speed_mps < 0.3:
        return []
    downwind_to = (wind_dir_deg + 180.0) % 360.0
    length_m = length_km * 1000.0
    vertices: list[tuple[float, float]] = [(source.lat, source.lon)]
    # Sweep the arc from left edge to right edge at the wedge tip.
    for i in range(arc_points):
        angle = -half_angle_deg + 2.0 * half_angle_deg * (i / (arc_points - 1))
        bearing = (downwind_to + angle) % 360.0
        east = math.sin(math.radians(bearing))
        north = math.cos(math.radians(bearing))
        lat, lon = offset_latlon(source.lat, source.lon, east * length_m, north * length_m)
        vertices.append((lat, lon))
    vertices.append((source.lat, source.lon))
    return vertices


def compute_downwind_zones(
    sources: Iterable[SourceEmission],
    districts: Iterable[District],
    weather: WeatherHour,
    half_angle_deg: float = 45.0,
    polygon_half_angle_deg: float = DEFAULT_HALF_ANGLE_DEG,
    wedge_length_km: float = DEFAULT_WEDGE_LENGTH_KM,
) -> list[dict]:
    """Build the per-source downwind zone payload for one weather hour.

    Each item is a dict suitable to be JSON-serialised into the forecast
    bundle and consumed by Folium / Streamlit:

        {
          "source_id", "source_name", "lat", "lon",
          "wind_dir_deg", "wind_speed_mps",
          "polygon": [[lat, lon], ...],
          "affected_districts": [
            {"district_id", "district_name", "score", "distance_km"},
            ...
          ],
          "max_score": float,
        }
    """
    sources_list = list(sources)
    districts_list = list(districts)
    out: list[dict] = []
    for source in sources_list:
        affected: list[dict] = []
        for district in districts_list:
            score = downwind_score(
                source, district,
                weather.wind_dir_deg, weather.wind_speed_mps,
                half_angle_deg=half_angle_deg,
            )
            if score <= 0:
                continue
            affected.append({
                "district_id": district.district_id,
                "district_name": district.name,
                "score": score,
                "distance_km": round(
                    haversine_km(source.lat, source.lon, district.lat, district.lon), 1
                ),
            })
        affected.sort(key=lambda r: r["score"], reverse=True)
        polygon = downwind_polygon(
            source, weather.wind_dir_deg, weather.wind_speed_mps,
            length_km=wedge_length_km,
            half_angle_deg=polygon_half_angle_deg,
        )
        max_score = max((r["score"] for r in affected), default=0.0)
        out.append({
            "source_id": source.source_id,
            "source_name": source.name,
            "lat": source.lat,
            "lon": source.lon,
            "wind_dir_deg": round(float(weather.wind_dir_deg), 1),
            "wind_speed_mps": round(float(weather.wind_speed_mps), 2),
            "polygon": [[round(lat, 5), round(lon, 5)] for lat, lon in polygon],
            "affected_districts": affected,
            "max_score": round(max_score, 4),
        })
    return out


def district_downwind_risk(zones: Iterable[dict], district_id: str) -> float:
    """Highest downwind score onto ``district_id`` across all sources."""
    best = 0.0
    for zone in zones:
        for affected in zone.get("affected_districts", ()):
            if affected.get("district_id") == district_id:
                score = float(affected.get("score", 0.0))
                if score > best:
                    best = score
    return round(best, 4)
