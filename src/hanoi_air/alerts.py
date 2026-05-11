from __future__ import annotations

import json
import urllib.request
from collections.abc import Iterable, Mapping
from datetime import datetime

from .logging_setup import get_logger
from .schemas import Alert

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
