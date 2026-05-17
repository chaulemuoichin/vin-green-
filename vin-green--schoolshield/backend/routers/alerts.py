from fastapi import APIRouter
from pydantic import BaseModel
from datetime import datetime, timedelta
import uuid

router = APIRouter(prefix="/api/alerts", tags=["alerts"])

# In-memory store — resets on server restart (fine for prototype)
_store: list[dict] = [
    {
        "id": "a1",
        "message": "Mức PM2.5 vượt ngưỡng an toàn — đề nghị kích hoạt chế độ không nổ máy",
        "level": "high",
        "created_at": (datetime.now() - timedelta(minutes=12)).isoformat(),
        "dismissed": False,
    },
    {
        "id": "a2",
        "message": "Phát hiện 8 phương tiện đang nổ máy chờ trước cổng trường",
        "level": "medium",
        "created_at": (datetime.now() - timedelta(minutes=28)).isoformat(),
        "dismissed": True,
    },
    {
        "id": "a3",
        "message": "Chất lượng không khí trở về mức an toàn sau can thiệp",
        "level": "low",
        "created_at": (datetime.now() - timedelta(hours=1, minutes=5)).isoformat(),
        "dismissed": True,
    },
]

class DismissRequest(BaseModel):
    id: str

@router.get("")
def get_alerts():
    return _store

@router.post("/dismiss")
def dismiss_alert(body: DismissRequest):
    for alert in _store:
        if alert["id"] == body.id:
            alert["dismissed"] = True
            return {"ok": True}
    return {"ok": False, "error": "not found"}
