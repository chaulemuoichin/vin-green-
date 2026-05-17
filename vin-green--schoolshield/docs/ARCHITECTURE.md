# Architecture

## System Overview

```
┌─────────────────────────────────────────────────────────┐
│  Browser  (localhost:5173)                               │
│                                                          │
│  React 18 app                                            │
│  ├─ useAQI hook    polls every 5 s  ─────────────────┐  │
│  ├─ useAlerts hook polls every 10 s ──────────────┐  │  │
│  └─ UI renders from hook state                    │  │  │
└───────────────────────────────────────────────────┼──┼──┘
                                                    │  │
          Vite dev server proxies /api/*  ◄──────────┘  │
                        │                               │
                        ▼                               │
┌─────────────────────────────────────────────────────┐  │
│  FastAPI  (localhost:8000)                           │  │
│                                                      │  │
│  GET /api/sensor/current  →  simulator.current_pm25()│  │
│  GET /api/sensor/history  →  simulator.history(30)   │◄─┘
│  GET /api/alerts          →  in-memory _store        │
│  POST /api/alerts/dismiss →  mutates _store          │
└─────────────────────────────────────────────────────┘
```

**No database. No real sensors.** All readings come from `simulator.py` at request time.

---

## Data Flow — Step by Step

```
1.  App mounts
    └─ useAQI calls GET /api/sensor/history → populates 30-min chart
    └─ useAlerts calls GET /api/alerts → shows alert log

2.  Every 5 seconds
    └─ useAQI calls GET /api/sensor/current
       └─ returns { pm25, risk, idling_count, timestamp }
       └─ Dashboard.jsx updates pm25, risk, idling state

3.  Dashboard.jsx side-effects on risk change
    └─ document.body.dataset.risk = risk
       └─ CSS variables update → background glow transitions over 2.5s
    └─ if risk === 'high' && alerts.length > 0:
       └─ setExpandedAlert(alerts[0].id)
       └─ alertLogRef.current.scrollIntoView()
    └─ if risk === 'high' && soundEnabled && prevRisk !== 'high':
       └─ AudioContext plays 520 Hz chime for 0.18s

4.  Props flow down
    └─ Dashboard → ParentView: pm25, risk, alerts, history
    └─ Dashboard → IdlingTicker: idling, risk
    └─ Dashboard → TrendChart: history (last 30 data points)
```

---

## Frontend Component Tree

```
App.jsx  (React Router)
│
├── /              Landing.jsx       Splash / entry
├── /login         Login.jsx         School login form
└── /dashboard     Dashboard.jsx     Main shell
    │
    ├── Header (inline in Dashboard.jsx)
    │   ├── SchoolShield logo
    │   ├── PersonaToggle              "Nhà trường" | "Phụ huynh"
    │   ├── Live dot + "Đang theo dõi"
    │   ├── Clock                      HH:MM:SS, updates every 1s
    │   ├── SoundButton                🔔/🔕 chime toggle
    │   ├── Mobile link                → /mobile
    │   └── AlertBanner                sticky (school view + risk=high only)
    │
    ├── [persona = "school"]
    │   ├── Tab: "Bảng điều khiển"
    │   │   ├── AQIGauge               Semicircle, green→yellow→red
    │   │   ├── MapPin                 Leaflet map, school-gate marker
    │   │   ├── ActionChecklist        Only renders at risk=high
    │   │   ├── IdlingTicker           Count + CO₂ + pulse border at high
    │   │   ├── Stat (PM2.5)           Current reading
    │   │   ├── Stat (active alerts)   Count
    │   │   ├── Stat (exposure mins)   Minutes above 35 µg/m³ today
    │   │   ├── TrendChart             30-min actual + 30-min forecast
    │   │   └── Alert log              groupedAlerts, expandable rows
    │   │
    │   └── Tab: "Phân tích"
    │       └── Analytics.jsx          Historical bar charts, alert table
    │
    ├── [persona = "parent"]
    │   └── ParentView.jsx
    │       ├── Status card            THẤP/CẦN LƯU Ý/NGUY HIỂM
    │       │                          PM2.5 value
    │       │                          "Cao hơn X% so với TB Hà Nội"
    │       │                          Share to Zalo button
    │       ├── Pickup card            Best pickup time
    │       │                          3-hour PM forecast bars (+1h/+2h/+3h)
    │       ├── Tips card              Risk-level health recommendations
    │       ├── Pattern chart          Typical daily PM2.5 shape (static)
    │       └── Active alerts          Pulsing dots, Vietnamese message
    │
    └── /mobile    MobileView.jsx      Mobile-optimised layout
```

---

## Risk System

Risk is computed **server-side** in `backend/simulator.py:risk_level()`.

| `risk` value | Condition | Background CSS | Other effects |
|---|---|---|---|
| `"low"` | PM2.5 < 35 | Green radial glow | — |
| `"medium"` | 35 ≤ PM2.5 < 75 | Yellow radial glow | — |
| `"high"` | PM2.5 ≥ 75 | Deep red glow, 3 radial spots | Alert banner, chime, idling pulse, auto-scroll |

The background is driven by three CSS custom properties (`--risk-glow-a/b/c`) set on `body[data-risk]`. The 2.5-second `transition` on `body` makes risk changes feel smooth rather than jarring.

---

## Simulator Model

```python
# backend/simulator.py

def _base_pm25(hour: float) -> float:
    morning   = 105 * exp(-0.5 * ((hour - 7.5)  / 0.5) ** 2)
    afternoon =  95 * exp(-0.5 * ((hour - 16.0) / 0.5) ** 2)
    return 30.0 + morning + afternoon

def current_pm25() -> float:
    hour = datetime.now().hour + datetime.now().minute / 60
    return max(8.0, round(_base_pm25(hour) + gauss(0, 5), 1))
```

The identical formula is **duplicated** in two frontend files:
- `TrendChart.jsx` — generates the 30-minute forecast overlay without an extra API call
- `ParentView.jsx` — computes the +1h/+2h/+3h pickup prediction bars

This is intentional for a hackathon prototype. Don't extract it to a shared module unless you're doing a proper refactor.

---

## Alert Grouping

`groupAlerts()` in `Dashboard.jsx` runs before render:

```
Input:  raw alerts array (unsorted, from API)
Step 1: sort ascending by created_at
Step 2: iterate — if current alert has same level as previous group
        AND is within 10 minutes of the group's last alert:
          increment count, update endTime, rewrite message
        else: start a new group
Output: grouped array (ascending) — rendered in reverse order (newest first)
```

Grouped alert message format: `"${count} lần ${levelLabel} liên tục — ${startTime} đến ${endTime}"`

---

## Replacing the Simulator with Real Hardware

The frontend only consumes the API contract. To connect real sensors:

1. **Replace `simulator.current_pm25()`** in `routers/sensor.py` with a serial/MQTT/HTTP read from the actual sensor
2. **Add a database** (SQLite is enough for a single school gate). Store each reading with its timestamp and replace `simulator.history()` with a DB query for the last 30 minutes
3. **Auto-generate alerts** — add a background task in `main.py` that watches incoming readings and writes to the alerts table when thresholds are crossed, instead of the static seed in `routers/alerts.py`

Frontend changes needed: none.
