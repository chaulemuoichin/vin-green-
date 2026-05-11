from __future__ import annotations

from pathlib import Path

from .weather import wind_components


def load_era5_point(path: Path, lat: float, lon: float, time_index: int = -1) -> dict | None:
    """Read a local ERA5 NetCDF point for weather backfill.

    ERA5 is not a 1h live source. This helper is intentionally local-file only;
    downloading from CDS should happen in an offline data preparation job.
    """
    try:
        import xarray as xr  # type: ignore
    except Exception:
        return None
    if not path.exists():
        return None
    try:
        dataset = xr.open_dataset(path)
        point = dataset.sel(latitude=lat, longitude=lon, method="nearest")
        if "time" in point.dims:
            point = point.isel(time=time_index)
        u10 = float(point["u10"].values)
        v10 = float(point["v10"].values)
        speed = (u10**2 + v10**2) ** 0.5
        # Meteorological direction from u/v.
        import math

        direction_from = (math.degrees(math.atan2(-u10, -v10)) + 360.0) % 360.0
        u_check, v_check = wind_components(speed, direction_from)
        return {
            "wind_speed_mps": speed,
            "wind_dir_deg": direction_from,
            "wind_u": u_check,
            "wind_v": v_check,
            "source": "ERA5",
        }
    except Exception:
        return None
