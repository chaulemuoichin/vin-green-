"""Translate per-district fire risks into actionable alerts.

Consumes :class:`hanoi_air.fire_risk.FireRisk` objects and emits
:class:`hanoi_air.schemas.Alert` rows for any district whose projected
risk crosses a configurable threshold. Messages are Vietnamese and
include the ETA in hours so the dashboard / webhook receiver can show
"Cháy Lào đến Hoàn Kiếm sau 14h, +18 µg/m³ PM2.5".
"""

from __future__ import annotations

from collections.abc import Iterable
from datetime import datetime, timedelta, timezone

from .fire_risk import FireRisk
from .schemas import Alert

DEFAULT_RISK_THRESHOLD: float = 0.30


def _severity_for_risk(risk: float) -> str:
    if risk >= 0.70:
        return "red"
    if risk >= 0.45:
        return "orange"
    return "yellow"


def fire_alert_messages(
    fire_risks: Iterable[FireRisk],
    risk_threshold: float = DEFAULT_RISK_THRESHOLD,
    now: datetime | None = None,
) -> list[Alert]:
    """Return one Alert per district whose fire risk exceeds the threshold."""
    now = now or datetime.now(timezone.utc)
    alerts: list[Alert] = []
    for fr in fire_risks:
        if fr.risk < risk_threshold:
            continue
        timestamp = now + timedelta(hours=max(0.0, fr.arrival_h))
        message = (
            f"Cháy {fr.origin} đến {fr.district_name} sau "
            f"{fr.arrival_h:.0f}h, AQI ước tính +{fr.pm25_delta:.0f} µg/m³ PM2.5 "
            f"({fr.detection_count} hotspot)."
        )
        alerts.append(Alert(
            district_id=fr.district_id,
            district_name=fr.district_name,
            timestamp=timestamp,
            pollutant="FIRE_PM25",
            value=round(fr.pm25_delta, 1),
            threshold=round(risk_threshold * 100, 0),
            severity=_severity_for_risk(fr.risk),
            message=message,
        ))
    return alerts
