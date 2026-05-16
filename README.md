# SchoolShield

Real-time school-gate air quality and vehicle-idling monitor built for the **Asian Hackathon for Green Future 2026**.

Tracks PM2.5 levels at the school entrance and counts idling vehicles during drop-off/pick-up windows. Two views: a **school staff dashboard** (live gauges, trend chart, alert log) and a **parent view** (safe pickup time, health tips, Zalo-share).

---

## Quick Start (2 terminals)

**Prerequisites:** Python 3.10+, Node.js 18+

### Terminal 1 — Backend

```bash
cd backend
pip install -r requirements.txt
uvicorn main:app --reload --port 8000
```

API is now live at `http://localhost:8000`
Interactive docs at `http://localhost:8000/docs`

### Terminal 2 — Frontend

```bash
cd frontend
npm install
npm run dev
```

Dashboard opens at `http://localhost:5173`

> Vite automatically proxies `/api` requests to `:8000` so you don't need to touch CORS or env vars.

---

## Folder Structure

```
schoolshield/
│
├── backend/                  # Python FastAPI server
│   ├── main.py               # App entry point — registers routers, CORS
│   ├── simulator.py          # Fake PM2.5 data generator (no real hardware needed)
│   ├── requirements.txt      # Python dependencies
│   └── routers/
│       ├── sensor.py         # GET /api/sensor/current  GET /api/sensor/history
│       └── alerts.py         # GET /api/alerts          POST /api/alerts/dismiss
│
├── frontend/                 # React + Vite app
│   ├── index.html
│   ├── vite.config.js        # /api proxy → localhost:8000
│   ├── tailwind.config.js
│   └── src/
│       ├── main.jsx          # React entry
│       ├── App.jsx           # Router setup (Landing → Login → Dashboard)
│       ├── index.css         # Global styles, Tailwind, risk-glow variables
│       ├── context/
│       │   └── PersonaContext.jsx   # "school" vs "parent" persona state
│       ├── hooks/
│       │   ├── useAQI.js     # Polls /api/sensor/current every 5 s
│       │   └── useAlerts.js  # Fetches /api/alerts every 10 s
│       ├── pages/
│       │   ├── Landing.jsx   # Splash / entry page
│       │   ├── Login.jsx     # School login screen
│       │   ├── Dashboard.jsx # Main view — routes between school and parent views
│       │   ├── ParentView.jsx        # Parent persona view
│       │   ├── Analytics.jsx         # Historical charts (school tab)
│       │   ├── MobileView.jsx        # Mobile-optimised layout
│       │   └── DesktopDashboard.jsx
│       └── components/
│           ├── AQIGauge.jsx          # Animated semicircle gauge
│           ├── RiskBadge.jsx         # THẤP / TRUNG BÌNH / CAO pill
│           ├── AlertBanner.jsx       # Sticky red banner at high risk
│           ├── IdlingTicker.jsx      # Live idling vehicle count + CO₂ estimate
│           ├── TrendChart.jsx        # 30-min actual + 30-min forecast line chart
│           ├── ActionChecklist.jsx   # Risk-gated action items for staff
│           ├── HeatmapStrip.jsx      # Hour-by-hour PM2.5 heatmap strip
│           ├── MapPin.jsx            # Leaflet map with sensor pin
│           └── ParticleField.jsx     # Ambient particle animation
│
├── docs/
│   ├── ARCHITECTURE.md       # System design, data flow, component map
│   └── API.md                # Full API reference
│
└── scripts/
    ├── start-backend.sh      # One-command backend start (Linux/Mac)
    ├── start-backend.bat     # One-command backend start (Windows)
    ├── start-frontend.sh
    └── start-frontend.bat
```

---

## How the Simulator Works

There is no real hardware. `backend/simulator.py` generates plausible Hanoi school-gate PM2.5 readings using a Gaussian bell curve:

```
PM2.5(hour) = 30 + 105·exp(-((hour-7.5)/0.5)²) + 95·exp(-((hour-16.0)/0.5)²) + noise
```

- **Morning peak** peaks at 07:30 (~128 µg/m³) — school drop-off traffic
- **Afternoon peak** peaks at 16:00 (~122 µg/m³) — pick-up traffic
- **Off-peak baseline** floats around 30–38 µg/m³ (Hanoi background)
- Gaussian noise (`σ = 5`) is added each reading so values feel live

Idling vehicle count is derived from PM2.5: `idling ≈ (pm25/10) × 1.5 ± rand(2)`

To simulate **different scenarios**, edit the constants in `simulator.py`:
| Variable | Default | Effect |
|---|---|---|
| `baseline` | `30.0` | Raise to simulate constant heavy pollution |
| `morning` amplitude `105` | - | Morning peak height |
| `afternoon` amplitude `95` | - | Afternoon peak height |
| `σ = 0.5` (both peaks) | - | Wider σ = longer peak duration |

---

## Risk Levels

| Level | Vietnamese | PM2.5 | Color |
|---|---|---|---|
| Low | THẤP | < 35 µg/m³ | Green |
| Medium | TRUNG BÌNH | 35–75 µg/m³ | Yellow |
| High | CAO | > 75 µg/m³ | Red |

At **CAO**, the UI automatically: shows the sticky alert banner, deepens the background red glow, pulses the idling card border, auto-scrolls to the alert log, and (if the user enabled it) plays a soft chime.

---

## Tech Stack

| Layer | Technology |
|---|---|
| Frontend | React 18, Vite, Tailwind CSS |
| Charts | Recharts |
| Animation | Framer Motion |
| Map | Leaflet + React-Leaflet |
| Backend | Python FastAPI |
| Server | Uvicorn |
| Data | In-memory simulator (no DB) |

---

## Common Tasks for Teammates

### Change the school name / location
Edit `Dashboard.jsx` lines with `"THCS Nguyễn Trãi"` and `"Hoan Kiếm · Hà Nội"`.

### Add a new alert
POST to `/api/alerts/dismiss` isn't needed — just restart the backend to reset the in-memory store. To seed new alerts, edit the `_store` list in `backend/routers/alerts.py`.

### Change the polling interval
In `frontend/src/hooks/useAQI.js`, find `setInterval` and change `5000` (ms).

### Force a specific risk level for testing
In `backend/simulator.py`, temporarily replace `current_pm25()` with a hardcoded value like `return 90.0` (triggers high risk).

### Run on a different port
Backend: `uvicorn main:app --port 9000`
Frontend: update `vite.config.js` proxy target to match.

---

## API Reference

See [`docs/API.md`](docs/API.md) for the full contract.

Quick summary:

```
GET  /api/sensor/current   → { pm25, risk, idling_count, timestamp }
GET  /api/sensor/history   → [{ pm25, risk, timestamp }, ...]   # last 30 min
GET  /api/alerts           → [{ id, message, level, created_at, dismissed }]
POST /api/alerts/dismiss   body: { "id": "a1" }
```

---

## Troubleshooting

**`ModuleNotFoundError: No module named 'fastapi'`**
Run `pip install -r requirements.txt` from inside the `backend/` folder, not the root.

**Frontend shows no data / "Đang tải..."**
Make sure the backend is running on port 8000. Check `vite.config.js` proxy config.

**Map not loading**
Leaflet CSS is loaded from CDN in `index.html`. Check network connectivity.

**CORS errors in browser console**
You're not using the Vite proxy — you're hitting `:8000` directly. Use `:5173` only.

**Port already in use**
Kill the old process: `npx kill-port 5173` / `npx kill-port 8000`, then restart.
