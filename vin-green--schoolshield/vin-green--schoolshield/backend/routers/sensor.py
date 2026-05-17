from fastapi import APIRouter
from datetime import datetime
from simulator import current_pm25, risk_level, idling_count, history

router = APIRouter(prefix="/api/sensor", tags=["sensor"])

@router.get("/current")
def get_current():
    pm25 = current_pm25()
    return {
        "pm25": pm25,
        "risk": risk_level(pm25),
        "idling_count": idling_count(pm25),
        "timestamp": datetime.now().isoformat(),
    }

@router.get("/history")
def get_history():
    return history(30)
