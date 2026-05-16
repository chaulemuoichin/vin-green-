import math
import random
import time
from datetime import datetime, timedelta

def _base_pm25(hour: float) -> float:
    """Hanoi school-gate PM2.5 — elevated baseline + sharp peaks at drop-off/pick-up."""
    # Peaks: 07:30 morning, 16:00 afternoon — widened σ=0.5 → ~2h of elevated air
    morning   = 105 * math.exp(-0.5 * ((hour - 7.5)  / 0.5) ** 2)
    afternoon = 95  * math.exp(-0.5 * ((hour - 16.0) / 0.5) ** 2)
    # Baseline elevated (Hanoi background pollution is medium-range year-round)
    baseline = 30.0
    return baseline + morning + afternoon

def current_pm25() -> float:
    now = datetime.now()
    hour = now.hour + now.minute / 60.0
    base = _base_pm25(hour)
    noise = random.gauss(0, 5)
    return max(8.0, round(base + noise, 1))

def risk_level(pm25: float) -> str:
    if pm25 < 35:
        return "low"
    elif pm25 < 75:
        return "medium"
    return "high"

def idling_count(pm25: float) -> int:
    """Estimate idling vehicles from PM2.5 — higher pollution → more idlers."""
    base = int((pm25 / 10) * 1.5)
    return max(0, base + random.randint(-2, 2))

def history(minutes: int = 30):
    """Generate last N minutes of history."""
    now = datetime.now()
    records = []
    for i in range(minutes, 0, -1):
        ts = now - timedelta(minutes=i)
        hour = ts.hour + ts.minute / 60.0
        base = _base_pm25(hour)
        pm25 = max(8.0, round(base + random.gauss(0, 6), 1))
        records.append({
            "pm25": pm25,
            "risk": risk_level(pm25),
            "timestamp": ts.isoformat(),
        })
    return records
