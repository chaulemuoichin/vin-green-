# SchoolShield 🛡️

> Real-time school-gate air quality monitor — Asian Hackathon for Green Future 2026
> Track: Urban Air Quality & Climate Resilience

SchoolShield tracks PM2.5 pollution and idling vehicles at school entrances during morning drop-off and afternoon pick-up. It gives **school staff** a live operations dashboard and gives **parents** a simple "is it safe to pick up my child right now?" view — all in Vietnamese.

No real hardware required. A built-in simulator generates realistic Hanoi school-gate pollution patterns so the full demo works out of the box.

---

## Table of Contents

- [Features](#features)
- [Prerequisites](#prerequisites)
- [Setup](#setup)
- [Running the App](#running-the-app)
- [How It Works](#how-it-works)
- [Project Structure](#project-structure)
- [For Teammates](#for-teammates)
- [API Reference](#api-reference)
- [Troubleshooting](#troubleshooting)

---

## Features

### School Staff View (Nhà trường)
- **Live AQI gauge** — animated semicircle, shifts green → yellow → red as PM2.5 rises
- **Trend chart** — last 30 minutes of actual readings overlaid with a 30-minute Gaussian forecast
- **Idling vehicle ticker** — live count with real-time CO₂ accumulation estimate
- **Smart alert log** — consecutive same-level alerts within 10 minutes are grouped into one row (e.g. "3 lần CAO liên tục — 15:32 đến 15:41")
- **Risk-gated action checklist** — only appears when air quality hits CAO; gives staff concrete steps
- **Sound chime** — optional 🔔 button plays a soft 520 Hz tone the moment risk transitions to CAO
- **Analytics tab** — historical bar charts and full alert history

### Parent View (Phụ huynh)
- **Safe pickup time** — recommends the best afternoon window based on the daily pollution pattern
- **3-hour PM forecast bars** — colour-coded bar chart for +1h, +2h, +3h predicted PM2.5
- **Hanoi average comparison** — "Cao hơn X% so với TB Hà Nội" so parents understand local context
- **Health tips** — tiered advice based on current risk level (open windows / wear masks / pick up fast)
- **One-tap Zalo share** — copies a formatted status message to clipboard

### Ambient UI
- Background glow deepens from green → red as risk rises (2.5-second CSS transition)
- Idling card pulses with a red border at high risk
- Alert log auto-scrolls and auto-expands when risk hits CAO
- Floating particle field; density scales with PM2.5

---

## Prerequisites

| Requirement | Minimum version | Check |
|---|---|---|
| Python | 3.10 | `python --version` |
| pip | bundled with Python | `pip --version` |
| Node.js | 18 | `node --version` |
| npm | 9 | `npm --version` |

> **Windows users:** if `python` opens the Microsoft Store, use `python3` or install Python from [python.org](https://www.python.org/downloads/) and tick "Add to PATH".

---

## Setup

Clone the repo and `cd` into it:

```bash
git clone https://github.com/chaulemuoichin/vin-green-.git
cd vin-green-
git checkout schoolshield
cd schoolshield
```

### 1. Python — create a virtual environment (recommended)

```bash
# Create venv
python -m venv .venv

# Activate — Mac/Linux
source .venv/bin/activate

# Activate — Windows (PowerShell)
.venv\Scripts\Activate.ps1

# Activate — Windows (Command Prompt)
.venv\Scripts\activate.bat
```

Install dependencies:

```bash
cd backend
pip install -r requirements.txt
cd ..
```

### 2. Node.js — install frontend dependencies

```bash
cd frontend
npm install
cd ..
```

You only need to do this once. After that, just use the [run commands](#running-the-app) below.

---

## Running the App

You need **two terminals open at the same time.**

### Terminal 1 — Backend API

```bash
cd backend

# If you created a venv, activate it first (see Setup step 1)

uvicorn main:app --reload --port 8000
```

You should see:
```
INFO:     Uvicorn running on http://127.0.0.1:8000
INFO:     Application startup complete.
```

- API base: `http://localhost:8000`
- Interactive Swagger docs: `http://localhost:8000/docs`

### Terminal 2 — Frontend

```bash
cd frontend
npm run dev
```

You should see:
```
  VITE v5.x.x  ready in Xms
  ➜  Local:   http://localhost:5173/
```

Open `http://localhost:5173` in your browser. The app loads, connects to the backend, and starts showing live data.

> The Vite dev server automatically proxies all `/api` requests to `localhost:8000`. You never need to hit port 8000 directly from the browser.

### One-command scripts (alternative)

```bash
# Mac/Linux
./scripts/start-backend.sh   # Terminal 1
./scripts/start-frontend.sh  # Terminal 2

# Windows
scripts\start-backend.bat    # Terminal 1
scripts\start-frontend.bat   # Terminal 2
```

These scripts auto-install dependencies if missing.

---

## How It Works

### The Simulator

There is no real sensor hardware. `backend/simulator.py` generates realistic Hanoi school-gate PM2.5 readings every time the API is called, using a Gaussian model:

```
PM2.5(hour) = 30                                         ← background baseline
            + 105 × exp(−½ × ((hour − 7.5)  / 0.5)²)   ← morning drop-off peak
            + 95  × exp(−½ × ((hour − 16.0) / 0.5)²)   ← afternoon pick-up peak
            + gauss(0, 5)                                ← random noise
```

| Time | Typical PM2.5 | Why |
|---|---|---|
| 07:30 | ~128 µg/m³ | Morning drop-off peak |
| 09:00–15:00 | 30–45 µg/m³ | Low traffic period |
| 16:00 | ~122 µg/m³ | Afternoon pick-up peak |
| 18:30 | ~28 µg/m³ | Evening baseline |

### Risk Levels

| Level | Vietnamese | PM2.5 | What happens |
|---|---|---|---|
| Low | THẤP | < 35 µg/m³ | Green glow, no alerts |
| Medium | TRUNG BÌNH | 35–75 µg/m³ | Yellow glow, advisory |
| High | CAO | > 75 µg/m³ | Red glow, chime, alert banner, action checklist |

### Persona System

The toggle in the top-right switches between **Nhà trường** (school staff) and **Phụ huynh** (parent). Both views pull from the same live data but present completely different information.

---

## Project Structure

```
schoolshield/
│
├── README.md                        ← you are here
├── .gitignore
│
├── backend/                         ── Python FastAPI ──────────────────────
│   ├── main.py                      App entry: CORS config, router registration
│   ├── simulator.py                 PM2.5 + idling vehicle data generator
│   ├── requirements.txt             fastapi, uvicorn
│   └── routers/
│       ├── sensor.py                /api/sensor/current and /api/sensor/history
│       └── alerts.py                /api/alerts GET + POST /dismiss
│
├── frontend/                        ── React 18 + Vite ──────────────────────
│   ├── vite.config.js               /api proxy to :8000
│   ├── tailwind.config.js
│   └── src/
│       ├── App.jsx                  Routes: Landing → Login → Dashboard
│       ├── index.css                Global styles, Tailwind, CSS risk variables
│       ├── context/
│       │   └── PersonaContext.jsx   "school" | "parent" persona state
│       ├── hooks/
│       │   ├── useAQI.js            Polls /api/sensor/current every 5 s
│       │   └── useAlerts.js         Polls /api/alerts every 10 s
│       ├── pages/
│       │   ├── Landing.jsx          Entry/splash screen
│       │   ├── Login.jsx            School login
│       │   ├── Dashboard.jsx        Main shell — persona routing, alert logic
│       │   ├── ParentView.jsx       Parent persona: pickup time, health tips
│       │   ├── Analytics.jsx        Historical data (school tab)
│       │   └── MobileView.jsx       Mobile-optimised layout
│       └── components/
│           ├── AQIGauge.jsx         Animated semicircle gauge
│           ├── RiskBadge.jsx        THẤP / TRUNG BÌNH / CAO pill
│           ├── AlertBanner.jsx      Sticky dismissible banner (CAO only)
│           ├── IdlingTicker.jsx     Vehicle count + CO₂ + red pulse at high risk
│           ├── TrendChart.jsx       Recharts area chart, actual + forecast
│           ├── ActionChecklist.jsx  Staff action items (high risk only)
│           ├── HeatmapStrip.jsx     Hour-by-hour PM2.5 colour strip
│           ├── MapPin.jsx           Leaflet map with sensor marker
│           └── ParticleField.jsx    Floating particle ambient animation
│
├── docs/
│   ├── API.md                       Full API contract with example JSON
│   └── ARCHITECTURE.md              System design, data flow, component tree
│
└── scripts/
    ├── start-backend.sh / .bat      Auto-install + start backend
    └── start-frontend.sh / .bat     Auto-install + start frontend
```

---

## For Teammates

### Change the school name or location
Search for `"THCS Nguyễn Trãi"` and `"Hoan Kiếm · Hà Nội"` in `Dashboard.jsx` and `ParentView.jsx`.

### Force high risk for UI testing
In `backend/simulator.py`, temporarily hardcode the return value:
```python
def current_pm25() -> float:
    return 90.0   # always CAO — remove this line when done
```
Restart the backend after saving.

### Add or edit pre-seeded alerts
Edit the `_store` list at the top of `backend/routers/alerts.py`. The store resets to this list every time the backend restarts (no database — intentional for the prototype).

### Change how often the frontend polls
In `frontend/src/hooks/useAQI.js`, find the `setInterval` call and change `5000` (milliseconds) to whatever you need.

### Run the backend on a different port
```bash
uvicorn main:app --reload --port 9000
```
Then update `vite.config.js` — change the proxy target from `http://localhost:8000` to `http://localhost:9000`.

### Build the frontend for production
```bash
cd frontend
npm run build
# Output goes to frontend/dist/
```
Serve `dist/` with any static file server. Point a reverse proxy (nginx, Caddy) at the FastAPI backend for `/api` routes.

---

## API Reference

Full contract with example responses: [`docs/API.md`](docs/API.md)

```
GET  /api/sensor/current    →  { pm25, risk, idling_count, timestamp }
GET  /api/sensor/history    →  [ { pm25, risk, timestamp }, … ]   ← last 30 min
GET  /api/alerts            →  [ { id, message, level, created_at, dismissed } ]
POST /api/alerts/dismiss    ←  { "id": "a1" }
GET  /                      →  { "status": "SchoolShield API running" }
```

---

## Troubleshooting

**`ModuleNotFoundError: No module named 'fastapi'`**
You installed into the wrong Python environment, or forgot to activate the venv.
```bash
# Activate venv, then:
pip install -r requirements.txt
```

**Frontend loads but shows zeros / "Đang tải..."**
The backend isn't running, or it's on a different port. Check Terminal 1 for errors.

**`EADDRINUSE` — port already in use**
```bash
npx kill-port 5173    # or 8000
```
Then restart the relevant process.

**CORS error in browser console**
You're opening the app on `localhost:8000` directly instead of `localhost:5173`. Always use the Vite port (5173) — it handles the proxy.

**Map tile layer not loading (grey tiles)**
Leaflet tiles load from OpenStreetMap CDN. Check your internet connection.

**`uvicorn: command not found`**
Either the venv isn't activated, or the install failed. Run `pip install uvicorn` and try again.

**PowerShell blocks `.ps1` script execution**
```powershell
Set-ExecutionPolicy -Scope CurrentUser RemoteSigned
```
Then re-run the `.ps1` activation script.
