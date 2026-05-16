# API Reference

**Base URL (dev):** `http://localhost:8000`

**Interactive docs (Swagger UI):** `http://localhost:8000/docs`

No authentication. No API keys. All responses are `application/json`.

---

## Endpoints

| Method | Path | Description |
|---|---|---|
| GET | `/` | Health check |
| GET | `/api/sensor/current` | Latest PM2.5 reading |
| GET | `/api/sensor/history` | Last 30 minutes of readings |
| GET | `/api/alerts` | All alerts (active + dismissed) |
| POST | `/api/alerts/dismiss` | Mark an alert as dismissed |

---

## GET `/`

Health check. Confirms the server is running.

**Response**
```json
{
  "status": "SchoolShield API running"
}
```

---

## GET `/api/sensor/current`

Returns a single, freshly generated PM2.5 reading from the simulator.

**Response**
```json
{
  "pm25": 84.3,
  "risk": "high",
  "idling_count": 11,
  "timestamp": "2026-05-17T16:02:34.512310"
}
```

| Field | Type | Values | Description |
|---|---|---|---|
| `pm25` | float | ≥ 0 | PM2.5 concentration in µg/m³ |
| `risk` | string | `"low"` `"medium"` `"high"` | Derived from PM2.5 thresholds |
| `idling_count` | int | ≥ 0 | Estimated number of idling vehicles |
| `timestamp` | string | ISO 8601 | Server time of the reading |

**Risk thresholds:**
- `"low"` — PM2.5 < 35 µg/m³
- `"medium"` — 35 ≤ PM2.5 < 75 µg/m³
- `"high"` — PM2.5 ≥ 75 µg/m³

The frontend polls this endpoint every **5 seconds**.

---

## GET `/api/sensor/history`

Returns the last 30 minutes of readings — one synthetic data point per minute, going back in time from now.

**Response** — array of 30 objects, oldest first
```json
[
  {
    "pm25": 32.1,
    "risk": "low",
    "timestamp": "2026-05-17T15:33:00.000000"
  },
  {
    "pm25": 47.8,
    "risk": "medium",
    "timestamp": "2026-05-17T15:34:00.000000"
  }
]
```

| Field | Type | Description |
|---|---|---|
| `pm25` | float | PM2.5 for that minute |
| `risk` | string | Risk level for that reading |
| `timestamp` | string | ISO 8601 timestamp of the minute |

The frontend fetches this once on mount to seed the trend chart.

---

## GET `/api/alerts`

Returns all alerts in the in-memory store — both active and dismissed. The store is seeded with three example alerts on server start and resets when the backend restarts.

**Response** — array
```json
[
  {
    "id": "a1",
    "message": "Mức PM2.5 vượt ngưỡng an toàn — đề nghị kích hoạt chế độ không nổ máy",
    "level": "high",
    "created_at": "2026-05-17T15:50:12.431000",
    "dismissed": false
  },
  {
    "id": "a2",
    "message": "Phát hiện 8 phương tiện đang nổ máy chờ trước cổng trường",
    "level": "medium",
    "created_at": "2026-05-17T15:34:00.000000",
    "dismissed": true
  }
]
```

| Field | Type | Description |
|---|---|---|
| `id` | string | Unique identifier |
| `message` | string | Vietnamese alert text |
| `level` | string | `"low"` `"medium"` `"high"` |
| `created_at` | string | ISO 8601 creation time |
| `dismissed` | boolean | `true` if staff has dismissed it |

The frontend polls this endpoint every **10 seconds**.

---

## POST `/api/alerts/dismiss`

Marks an alert as dismissed (`dismissed: true`). Dismissed alerts remain in the store and are still returned by GET `/api/alerts` — the frontend filters them out of the active alert count.

**Request body**
```json
{ "id": "a1" }
```

**Response — success**
```json
{ "ok": true }
```

**Response — alert not found**
```json
{ "ok": false, "error": "not found" }
```

---

## Error Handling

The backend does not return HTTP error codes for most prototype scenarios — it returns `{ "ok": false, "error": "..." }` in the response body. For real production use, switch to proper HTTP status codes (404, 422, etc.).

FastAPI's built-in 422 validation error fires automatically if you POST a malformed body (e.g. missing `id` field):

```json
{
  "detail": [
    {
      "loc": ["body", "id"],
      "msg": "field required",
      "type": "value_error.missing"
    }
  ]
}
```
