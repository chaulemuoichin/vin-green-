from __future__ import annotations

import math
from collections.abc import Iterable, Mapping

from .schemas import SourceEmission
from .weather import latlon_to_local_m, wind_to_unit


def gaussian_plume_concentration(
    source: SourceEmission,
    target_lat: float,
    target_lon: float,
    wind_speed_mps: float,
    wind_dir_deg: float,
    pollutant: str = "pm25",
) -> float:
    """AERMOD-style Gaussian plume approximation for MVP downwind tracking.

    This is not a regulatory AERMOD calculation. It supplies a physically
    oriented source contribution that can later be replaced by AERMOD/HYSPLIT.
    """
    if source.status != "active":
        return 0.0
    q_g_s = source.pm25_g_s if pollutant == "pm25" else source.no2_g_s
    if q_g_s <= 0:
        return 0.0

    dx, dy = latlon_to_local_m(source.lat, source.lon, target_lat, target_lon)
    wind_east, wind_north = wind_to_unit(wind_dir_deg)
    x_downwind = dx * wind_east + dy * wind_north
    y_crosswind = -dx * wind_north + dy * wind_east
    if x_downwind <= 0:
        return 0.0

    wind_speed = max(0.8, wind_speed_mps)
    sigma_y = max(18.0, 0.12 * x_downwind * (1.0 + 0.0001 * x_downwind) ** -0.5)
    sigma_z = max(12.0, 0.08 * x_downwind * (1.0 + 0.0002 * x_downwind) ** -0.5)
    q_ug_s = q_g_s * 1_000_000.0
    vertical = math.exp(-0.5 * (source.height_m / sigma_z) ** 2)
    crosswind = math.exp(-0.5 * (y_crosswind / sigma_y) ** 2)
    concentration = q_ug_s / (2.0 * math.pi * wind_speed * sigma_y * sigma_z) * crosswind * vertical
    return max(0.0, min(concentration, 90.0 if pollutant == "pm25" else 220.0))


def plume_contribution(
    sources: Iterable[SourceEmission],
    target_lat: float,
    target_lon: float,
    wind_speed_mps: float,
    wind_dir_deg: float,
) -> Mapping[str, float]:
    pm25 = 0.0
    no2 = 0.0
    for source in sources:
        pm25 += gaussian_plume_concentration(
            source, target_lat, target_lon, wind_speed_mps, wind_dir_deg, "pm25"
        )
        no2 += gaussian_plume_concentration(
            source, target_lat, target_lon, wind_speed_mps, wind_dir_deg, "no2"
        )
    return {"pm25": pm25, "no2": no2}
