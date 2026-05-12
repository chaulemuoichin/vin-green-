from __future__ import annotations

import json
import urllib.request
from collections.abc import Iterable, Mapping
from datetime import datetime, timedelta, timezone

from .logging_setup import get_logger
from .schemas import Alert, FireDetection

logger = get_logger(__name__)


def generate_alerts(
    forecasts: Iterable[Mapping[str, object]],
    aqi_threshold: int = 150,
    pm25_threshold: float = 55.5,
) -> list[Alert]:
    first_by_district: dict[str, Alert] = {}
    for row in forecasts:
        district_id = str(row["district_id"])
        if district_id in first_by_district:
            continue
        aqi = int(row["aqi"])
        pm25 = float(row["pm25"])
        timestamp = datetime.fromisoformat(str(row["timestamp"]))
        if aqi > aqi_threshold or pm25 >= pm25_threshold:
            pollutant = "AQI" if aqi > aqi_threshold else "PM2.5"
            value = float(aqi if pollutant == "AQI" else pm25)
            threshold = float(aqi_threshold if pollutant == "AQI" else pm25_threshold)
            severity = "red" if aqi >= 200 else "orange"
            first_by_district[district_id] = Alert(
                district_id=district_id,
                district_name=str(row["district_name"]),
                timestamp=timestamp,
                pollutant=pollutant,
                value=value,
                threshold=threshold,
                severity=severity,
                message=str(row["health_text"]),
            )
    return list(first_by_district.values())


def _bearing_to_direction(bearing: float) -> str:
    dirs = ["Bắc", "Đông Bắc", "Đông", "Đông Nam", "Nam", "Tây Nam", "Tây", "Tây Bắc"]
    return dirs[int((bearing + 22.5) / 45) % 8]


def generate_fire_alerts(
    high_risk_fires: list[FireDetection],
    low_risk_fires: list[FireDetection],
    wind_speed_850hpa_kmh: float,
    wind_dir_850hpa_deg: float,
) -> list[Alert]:
    """Generate city-wide alerts for high-risk upwind fires.

    Only fires already filtered to risk_score > threshold are processed.
    Skips fires whose estimated smoke arrival exceeds 24h or when wind is stagnant.
    """
    now = datetime.now(timezone.utc)
    alerts: list[Alert] = []

    if wind_speed_850hpa_kmh < 5.0:
        logger.debug("fire_alerts: wind too weak (%.1f km/h), no smoke transport expected", wind_speed_850hpa_kmh)
        return alerts

    for fire in high_risk_fires:
        arrival_hours = fire.distance_to_hanoi_km / wind_speed_850hpa_kmh
        if arrival_hours > 24.0:
            continue

        direction = _bearing_to_direction(fire.bearing_from_hanoi_deg)
        severity = "red" if fire.risk_score > 0.6 else ("orange" if fire.risk_score > 0.4 else "yellow")
        arrival_str = (now + timedelta(hours=arrival_hours)).strftime("%H:%M %d/%m")

        alerts.append(
            Alert(
                district_id="all",
                district_name="Hà Nội",
                timestamp=now,
                pollutant="fire_smoke",
                value=round(fire.frp, 1),
                threshold=50.0,
                severity=severity,
                message=(
                    f"Cháy rừng {fire.distance_to_hanoi_km:.0f}km về phía {direction}. "
                    f"Cường độ: {fire.frp:.0f} MW. "
                    f"Khói dự kiến ~{arrival_hours:.0f}h ({arrival_str}). "
                    f"Rủi ro: {fire.risk_score:.0%}."
                ),
            )
        )

    if low_risk_fires:
        logger.info(
            "fire_alerts: %d high-risk, %d low-risk skipped (saved ~%.0f min HYSPLIT compute)",
            len(high_risk_fires),
            len(low_risk_fires),
            len(low_risk_fires) * 3 * 45 / 60,
        )

    return alerts


def post_alerts(alerts: Iterable[Alert], webhook_url: str | None) -> bool:
    if not webhook_url:
        return False
    payload = json.dumps({"alerts": [alert.to_dict() for alert in alerts]}).encode("utf-8")
    request = urllib.request.Request(
        webhook_url,
        data=payload,
        headers={"Content-Type": "application/json", "User-Agent": "hanoi-air-forecast/0.1"},
        method="POST",
    )
    try:
        with urllib.request.urlopen(request, timeout=10):
            return True
    except Exception as exc:
        logger.warning("alert webhook POST failed: {exc}", exc=exc)
        return False
