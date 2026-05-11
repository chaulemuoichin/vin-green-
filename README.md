# Hanoi Live Air Pollution Forecast

Hybrid live/demo system for 24h PM2.5, NO2, AQI forecasting across Hanoi's 30 district-level areas. It blends sparse station observations, free forecast APIs, wind vector fields, traffic proxies, and AERMOD-style Gaussian plume contribution for downwind alerts.

## What Is Included

- `notebooks/01_hanoi_air_live_prototype.ipynb`: first Jupyter prototype for ingestion, LSTM smoke training, plume forecast, and Bắc Từ Liêm map.
- `src/hanoi_air/`: reusable core package.
- `app/streamlit_app.py`: interactive Streamlit + Folium dashboard.
- `api/main.py`: FastAPI endpoints for health, districts, forecasts, and alerts.
- `worker/tasks.py`: Celery-compatible 30-minute refresh task.
- `data/sample/`: sample station, weather, traffic, factory, and parser payload data.
- `tests/`: pytest coverage for adapters, interpolation, wind/plume, LSTM smoke, forecast, alerts, API, and top-5 report.

## Data Priority

The live pipeline prefers free/public sources before falling back to sample data:

1. Open-Meteo Weather Forecast API for wind/weather, no key required.
2. Open-Meteo Air Quality API for 24h PM2.5/NO2 background, no key required.
3. AQICN station observations when `AQICN_TOKEN` is configured.
4. OpenAQ observations when `OPENAQ_API_KEY` is configured.
5. Public SOMO/CEM page crawlers every 30-60 minutes, with local raw archive and no login/captcha bypass.
6. Sample data in `data/sample` when live sources are unavailable.

Raw fetched/crawled payloads are archived under `data/raw/{source}/YYYY-MM-DD/`. Normalized records are appended under `data/processed/` for backtesting and calibration.

## Setup

```powershell
python -m venv .venv
.venv\Scripts\Activate.ps1
python -m pip install -r requirements.txt
```

For live data, copy `.env.example` to `.env` or set environment variables directly:

```powershell
$env:AQICN_TOKEN="your_token"
$env:OPENAQ_API_KEY="your_key"
$env:OPENWEATHER_API_KEY="your_key"
$env:REDIS_URL="redis://localhost:6379/0"
```

Without keys, Open-Meteo still supplies free weather/air-quality background when network is available; otherwise every entrypoint falls back to `data/sample`.

Scheduler/cache defaults are 30 minutes:

```powershell
$env:CACHE_TTL_SECONDS="1800"
$env:ENABLE_PUBLIC_CRAWL="true"
$env:ENABLE_OVERPASS="false"
```

## Run with Docker (Recommended)

The fastest way to get the full stack running is with Docker Compose:

```powershell
# Copy and configure environment
cp .env.example .env
# Edit .env with your API keys (AQICN_TOKEN, OPENAQ_API_KEY, etc.)

# Start all services (Redis, API, Worker, Dashboard)
make up

# View logs
make logs

# Stop services
make down
```

This starts:
- **Dashboard** (Streamlit): http://localhost:8501
- **API** (FastAPI): http://localhost:8000 (docs at http://localhost:8000/docs)
- **Worker** (Celery): Background tasks every 30 min
- **Redis**: Cache & message broker (port 6379)

For other Docker commands, see the `Makefile`:

```powershell
make help    # Show all available commands
make build   # Rebuild Docker image
make clean   # Remove containers and volumes
```

## Run Locally (Development)

```powershell
# Local dev mode (no Docker, Streamlit + API + Worker)
make dev
```

## Run

Notebook:

```powershell
jupyter notebook notebooks\01_hanoi_air_live_prototype.ipynb
```

Streamlit dashboard:

```powershell
streamlit run app\streamlit_app.py
```

FastAPI:

```powershell
uvicorn api.main:app --reload
```

Top-5 worst districts for tomorrow:

```powershell
python scripts\top5_forecast.py
```

Tests:

```powershell
python -m pytest
```

## API

- `GET /health`
- `GET /districts`
- `GET /forecast?district_id=bac_tu_liem&hour_offset=6&use_live=false`
- `GET /alerts?use_live=false`

## Modeling Notes

The current plume model is a pure-Python Gaussian plume approximation, designed as a pluggable MVP. It is not a regulatory AERMOD run. External AERMOD/HYSPLIT can be added behind the same dispersion interface once binaries and met/terrain data are available.

The LSTM component is implemented with PyTorch when installed, with a deterministic fallback for smoke tests. Production training should use validated historical AQICN/SOMO/OpenAQ/Open-Meteo/OpenWeather/ERA5 data and persist trained weights.

Open-Meteo/CAMS background is bias-corrected with fresh station observations when available. Station/crawl data receive quality flags such as `live_api`, `public_crawl`, `forecast_background`, and `sample`; source freshness is tracked in `.cache/source_status.json`.
