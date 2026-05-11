from __future__ import annotations

import csv
import math
from collections.abc import Iterable
from pathlib import Path

from .config import get_settings
from .schemas import District

EARTH_RADIUS_KM = 6371.0088


def load_districts(path: Path | None = None) -> list[District]:
    settings = get_settings()
    csv_path = path or settings.sample_dir / "districts.csv"
    districts: list[District] = []
    with csv_path.open("r", encoding="utf-8", newline="") as handle:
        for row in csv.DictReader(handle):
            districts.append(
                District(
                    district_id=row["district_id"],
                    name=row["name"],
                    lat=float(row["lat"]),
                    lon=float(row["lon"]),
                    population=int(float(row.get("population") or 0)),
                    area_km2=float(row.get("area_km2") or 0.0),
                    urban_level=row.get("urban_level") or "mixed",
                )
            )
    return districts


def haversine_km(lat1: float, lon1: float, lat2: float, lon2: float) -> float:
    phi1 = math.radians(lat1)
    phi2 = math.radians(lat2)
    d_phi = math.radians(lat2 - lat1)
    d_lambda = math.radians(lon2 - lon1)
    a = math.sin(d_phi / 2) ** 2 + math.cos(phi1) * math.cos(phi2) * math.sin(d_lambda / 2) ** 2
    return 2 * EARTH_RADIUS_KM * math.atan2(math.sqrt(a), math.sqrt(1 - a))


def nearest_district(
    lat: float, lon: float, districts: Iterable[District] | None = None
) -> District:
    candidates = list(districts) if districts is not None else load_districts()
    return min(candidates, key=lambda d: haversine_km(lat, lon, d.lat, d.lon))


def district_by_id(district_id: str, districts: Iterable[District] | None = None) -> District:
    candidates = list(districts) if districts is not None else load_districts()
    for district in candidates:
        if district.district_id == district_id:
            return district
    raise KeyError(f"Unknown district_id: {district_id}")


def district_features(districts: Iterable[District] | None = None) -> dict:
    """Return small square polygons around centroids for lightweight Folium display."""
    features = []
    for district in list(districts) if districts is not None else load_districts():
        delta = 0.018 if district.urban_level == "urban" else 0.035
        lon = district.lon
        lat = district.lat
        polygon = [
            [lon - delta, lat - delta],
            [lon + delta, lat - delta],
            [lon + delta, lat + delta],
            [lon - delta, lat + delta],
            [lon - delta, lat - delta],
        ]
        features.append(
            {
                "type": "Feature",
                "properties": district.to_dict(),
                "geometry": {"type": "Polygon", "coordinates": [polygon]},
            }
        )
    return {"type": "FeatureCollection", "features": features}
