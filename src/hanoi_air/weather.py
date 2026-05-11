from __future__ import annotations

import math


def wind_components(speed_mps: float, direction_from_deg: float) -> tuple[float, float]:
    """Convert meteorological wind direction to u/v components.

    Direction is the bearing the wind blows from. u is positive eastward and v
    is positive northward.
    """
    theta = math.radians(direction_from_deg % 360)
    u = -float(speed_mps) * math.sin(theta)
    v = -float(speed_mps) * math.cos(theta)
    return u, v


def wind_to_unit(direction_from_deg: float) -> tuple[float, float]:
    """Return east/north unit vector for the downwind direction."""
    direction_to_deg = (direction_from_deg + 180.0) % 360.0
    theta = math.radians(direction_to_deg)
    return math.sin(theta), math.cos(theta)


def wind_direction_text(direction_from_deg: float) -> str:
    sectors = [
        "bắc",
        "đông bắc",
        "đông",
        "đông nam",
        "nam",
        "tây nam",
        "tây",
        "tây bắc",
    ]
    idx = int(((direction_from_deg % 360) + 22.5) // 45) % 8
    return f"gió {sectors[idx]}"


def latlon_to_local_m(
    source_lat: float, source_lon: float, target_lat: float, target_lon: float
) -> tuple[float, float]:
    mean_lat = math.radians((source_lat + target_lat) / 2.0)
    meters_per_deg_lat = 111_320.0
    meters_per_deg_lon = 111_320.0 * math.cos(mean_lat)
    dx = (target_lon - source_lon) * meters_per_deg_lon
    dy = (target_lat - source_lat) * meters_per_deg_lat
    return dx, dy


def offset_latlon(lat: float, lon: float, east_m: float, north_m: float) -> tuple[float, float]:
    meters_per_deg_lat = 111_320.0
    meters_per_deg_lon = 111_320.0 * math.cos(math.radians(lat))
    return lat + north_m / meters_per_deg_lat, lon + east_m / meters_per_deg_lon
