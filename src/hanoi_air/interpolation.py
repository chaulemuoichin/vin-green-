from __future__ import annotations

import math
import os
from collections.abc import Iterable, Mapping

from .geography import haversine_km


def idw_interpolate(
    points: Iterable[Mapping[str, float]],
    targets: Iterable[Mapping[str, float]],
    power: float = 2.0,
    max_distance_km: float = 80.0,
) -> list[float]:
    """Inverse-distance weighted interpolation for sparse station readings."""
    source_points = list(points)
    values: list[float] = []
    for target in targets:
        weighted_sum = 0.0
        weight_total = 0.0
        nearest_value = None
        nearest_distance = float("inf")
        for point in source_points:
            distance = haversine_km(
                float(point["lat"]),
                float(point["lon"]),
                float(target["lat"]),
                float(target["lon"]),
            )
            if distance < nearest_distance:
                nearest_distance = distance
                nearest_value = float(point["value"])
            if distance < 1e-6:
                weighted_sum = float(point["value"])
                weight_total = 1.0
                break
            if distance <= max_distance_km:
                weight = 1.0 / (distance**power)
                weighted_sum += weight * float(point["value"])
                weight_total += weight
        if weight_total > 0:
            values.append(weighted_sum / weight_total)
        elif nearest_value is not None:
            values.append(nearest_value)
        else:
            values.append(math.nan)
    return values


def kriging_or_idw(
    points: Iterable[Mapping[str, float]],
    targets: Iterable[Mapping[str, float]],
    use_kriging: bool | None = None,
) -> list[float]:
    if use_kriging is None:
        use_kriging = os.getenv("USE_KRIGING", "false").strip().lower() in {"1", "true", "yes"}
    if not use_kriging:
        return idw_interpolate(points, targets)
    try:
        from pykrige.ok import OrdinaryKriging  # type: ignore
    except Exception:
        return idw_interpolate(points, targets)

    source_points = list(points)
    target_points = list(targets)
    if len(source_points) < 4:
        return idw_interpolate(source_points, target_points)
    lons = [float(p["lon"]) for p in source_points]
    lats = [float(p["lat"]) for p in source_points]
    vals = [float(p["value"]) for p in source_points]
    try:
        model = OrdinaryKriging(lons, lats, vals, variogram_model="linear", verbose=False)
        z, _ = model.execute(
            "points",
            [float(t["lon"]) for t in target_points],
            [float(t["lat"]) for t in target_points],
        )
        return [float(v) for v in z]
    except Exception:
        return idw_interpolate(source_points, target_points)
