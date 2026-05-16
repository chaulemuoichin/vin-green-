# API Reference

Base URL (dev): `http://localhost:8000`

Interactive Swagger UI: `http://localhost:8000/docs`

All responses are JSON. No authentication required (prototype).

---

## Sensor

### `GET /api/sensor/current`

Returns the latest simulated PM2.5 reading.

**Response**
```json
{
  "pm25": 84.3,
  "risk": "high",
  "idling_count": 11,
  "timestamp": "2026-05-17T16:02:34.512310"
}
```

| Field | Type | Description |
|---|---|---|
| `pm25` | float | PM2.5 concentration in µg/m³ |
| `risk` | string | `"low"` / `"medium"` / `"high"` |
| `idling_count` | int | Estimated idling vehicles |
| `timestamp` | ISO 8601 string | Server time of reading |

---

### `GET /api/sensor/history`

Returns the last 30 minutes of readings (one per minute).

**Response** — array of objects
```json
[
  { "pm25": 32.1, "risk": "low",  "timestamp": "2026-05-17T15:33:00" },
  { "pm25": 47.8, "risk": "medium", "timestamp": "2026-05-17T15:34:00" },
  ...
]
```

---

## Alerts

### `GET /api/alerts`

Returns all alerts (active + dismissed).

**Response**
```json
[
  {
    "id": "a1",
    "message": "Mức PM2.5 vượt ngưỡng an toàn — đề nghị kích hoạt chế độ không nổ máy",
    "level": "high",
    "created_at": "2026-05-17T15:50:12.431000",
    "dismissed": false
  },
  ...
]
```

| Field | Type | Description |
|---|---|---|
| `id` | string | Unique alert identifier |
| `message` | string | Vietnamese alert text |
| `level` | string | `"low"` / `"medium"` / `"high"` |
| `created_at` | ISO 8601 string | When the alert was created |
| `dismissed` | boolean | Whether staff has dismissed it |

---

### `POST /api/alerts/dismiss`

Marks an alert as dismissed.

**Request body**
```json
{ "id": "a1" }
```

**Response (success)**
```json
{ "ok": true }
```

**Response (not found)**
```json
{ "ok": false, "error": "not found" }
```

---

## Health check

### `GET /`

```json
{ "status": "SchoolShield API running" }
```
