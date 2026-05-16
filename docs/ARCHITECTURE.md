# Architecture

## System Overview

```
Browser (:5173)
    │
    │  React app
    │  polls every 5s
    │
    ▼
Vite dev server  ──/api proxy──►  FastAPI (:8000)
                                      │
                                  simulator.py
                               (generates fake data)
```

No database. No real sensors. All data is generated in-memory by `simulator.py` on each request.

---

## Data Flow

```
1. useAQI hook        → GET /api/sensor/current   (every 5 s)
2. useAQI hook        → GET /api/sensor/history   (on mount)
3. useAlerts hook     → GET /api/alerts            (every 10 s)

4. Dashboard.jsx reads pm25, risk, idling from useAQI
5. Sets document.body[data-risk] → CSS variables update background glow
6. Passes pm25+risk down to child components

7. When risk = "high":
   - AlertBanner renders (sticky)
   - Alert log auto-scrolls + first alert expands
   - Soft chime plays (if user enabled it)
   - IdlingTicker card pulses with red border
   - Background glow deepens (CSS transition 2.5s)
```

---

## Frontend Components

```
App.jsx
└── Router
    ├── Landing.jsx          Splash screen
    ├── Login.jsx            Login form
    └── Dashboard.jsx        Main shell
        │
        ├── Header
        │   ├── PersonaToggle  "Phụ huynh" / "Nhà trường"
        │   ├── Clock          Live HH:MM:SS
        │   ├── SoundButton    Toggle chime on CAO
        │   └── AlertBanner    Sticky banner (school view, risk=high only)
        │
        ├── [persona=school, tab=dashboard]
        │   ├── AQIGauge        Semicircle gauge, green→yellow→red
        │   ├── MapPin          Leaflet map, sensor marker
        │   ├── ActionChecklist Risk-gated action items (only at high)
        │   ├── IdlingTicker    Live count + CO₂ estimate + pulse at high
        │   ├── TrendChart      30-min actual + 30-min Gaussian forecast
        │   └── Alert log       Grouped alerts, expandable rows
        │
        ├── [persona=school, tab=analytics]
        │   └── Analytics.jsx   Bar charts, alert history table
        │
        └── [persona=parent]
            └── ParentView.jsx
                ├── Status card    Risk status + PM2.5 + Hanoi % comparison
                ├── Pickup card    Best pickup time + 3-hour PM forecast bars
                ├── Tips card      Health recommendations
                ├── Pattern chart  Typical daily PM2.5 (static shape)
                └── Active alerts  Pulsing alert dots
```

---

## Risk System

Risk is computed server-side in `simulator.py`:

| Level | Condition | CSS variable set |
|---|---|---|
| `low` | PM2.5 < 35 | default green glow |
| `medium` | 35 ≤ PM2.5 < 75 | yellow glow (`rgba(251,191,36,...)`) |
| `high` | PM2.5 ≥ 75 | red glow (`rgba(248,113,113,...)`), center spot |

The background uses CSS custom properties (`--risk-glow-a/b/c`) and a 2.5-second CSS transition, so the color shifts feel smooth.

---

## Simulator Model

```python
PM2.5(h) = 30 + 105·exp(-½·((h-7.5)/0.5)²)   # morning peak (07:30)
               + 95·exp(-½·((h-16.0)/0.5)²)   # afternoon peak (16:00)
               + gauss(0, 5)                   # noise
```

The same formula is duplicated in `frontend/src/components/TrendChart.jsx` (as `basePm25`) to generate the 30-minute forecast overlay without a backend call, and in `frontend/src/pages/ParentView.jsx` for the 3-hour pickup prediction bars.

---

## Adding Real Sensors

To swap the simulator for real hardware:

1. Replace `simulator.current_pm25()` in `routers/sensor.py` with a serial/MQTT read
2. Store readings in a real DB (SQLite → Postgres) and update `history()` to query it
3. Generate alerts automatically by watching PM2.5 thresholds instead of the static seed in `routers/alerts.py`

The frontend needs no changes — it only consumes the API contract.
