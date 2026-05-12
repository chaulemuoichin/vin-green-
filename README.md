# Hanoi Live Air Pollution Forecast

24-hour PM2.5 / NO₂ / AQI forecast for **15 Hanoi districts** (12 inner urban + Hoài Đức, Thạch Thất, Sơn Tây). The system blends sparse station observations, free forecast APIs, wind vector fields, traffic proxies, and a Gaussian plume contribution for downwind alerts — then explains every prediction with source attribution, downwind zones, and concrete actions for citizens and authorities.

> **30-second pitch.** "Hoàn Kiếm AQI 162 tomorrow 08:00 → wear N95 between 8–10 h. The model attributes 56 % to traffic and 17 % to the Minh Khai industrial cluster, currently downwind under SSE wind. Government action: truck restriction on Phạm Văn Đồng 6–10 h and 16–20 h; inspect the Minh Khai stack."

The forecast bundle exposes every layer judges or citizens might ask about: dual AQI scale (US-EPA *and* VN_AQI / QCVN), source-share pie, downwind risk per district, citizen + government action bullets, fire-alert ETA from regional biomass burning, and a 7-day backtest snapshot vs a persistence baseline.

## What Is Included

- `src/hanoi_air/`: core forecast pipeline, modular by concern (`forecast.py`, `dispersion.py`, `downwind.py`, `vn_aqi.py`, `source_breakdown.py`, `validation.py`, `actions.py`, `fire_risk.py`, `fire_alerts.py`, `lstm_wire.py`, …).
- `app/streamlit_app.py`: dark-glassmorphism Streamlit dashboard — map (heatmap + wind + downwind wedges) + 24 h chart + four detail tabs (VN_AQI · Nguồn ô nhiễm · Hành động · Độ chính xác).
- `api/main.py`: FastAPI service with `X-API-Key` auth and slowapi rate limits.
- `worker/tasks.py`: Celery 30-min refresh + daily archive cleanup beats.
- `scripts/`: `top5_forecast.py`, `run_backtest.py`, `cleanup_raw_archive.py`.
- `data/sample/`: 15 districts, factories, traffic corridors, station snapshots.
- `tests/`: 101 unit tests covering AQI math, IDW, plume, downwind bearings, source breakdown, fire alerts, actions, validation metrics, LSTM wiring, auth, and rate limiting — plus a skippable end-to-end suite.

## 1-click demo

```powershell
cp .env.example .env
# (optional) edit .env to set AQICN_TOKEN / OPENAQ_API_KEY for live data
make prod-build
make prod-up
```

Open `http://localhost/` — the dashboard. The API lives at `http://localhost/api/` behind the bundled nginx. Healthchecks settle in ~30 s. Stop with `make prod-down`.

| URL | Purpose |
| --- | --- |
| `http://localhost/` | Dashboard (Streamlit, dark glassmorphism) |
| `http://localhost/api/health` | API liveness |
| `http://localhost/api/forecast?district=hoan_kiem&hours=24` | District 24 h forecast (requires `X-API-Key` if `API_KEYS` is set) |
| `http://localhost/docs` | OpenAPI swagger |

## What's new in Week 1

| Feature | Where | Module |
| --- | --- | --- |
| VN_AQI (QCVN 06:2022 / Decision 1459/QĐ-TCMT) alongside US-EPA NowCast | "🇻🇳 VN_AQI" tab + every forecast row | [`vn_aqi.py`](src/hanoi_air/vn_aqi.py) |
| PM2.5 source attribution (traffic / industry / agriculture / fire / other) | "🥧 Nguồn ô nhiễm" tab + every row | [`source_breakdown.py`](src/hanoi_air/source_breakdown.py) |
| Downwind risk zones (Folium wedge polygons) | Map "Vùng xuôi gió" layer + `downwind_risk` per row | [`downwind.py`](src/hanoi_air/downwind.py) |
| Citizen + government actions (Vietnamese) | "✅ Hành động" tab + every row | [`actions.py`](src/hanoi_air/actions.py) |
| Fire alerts Phase 2 (FIRMS → district risk + ETA hours) | Alerts banner + tab | [`fire_risk.py`](src/hanoi_air/fire_risk.py), [`fire_alerts.py`](src/hanoi_air/fire_alerts.py) |
| Backtest framework (RMSE / MAE / R² vs persistence baseline) | "📐 Độ chính xác" tab + `scripts/run_backtest.py` | [`validation.py`](src/hanoi_air/validation.py) |
| LSTM ensemble gate (heuristic 0.7 + LSTM 0.3 when it beats baseline) | Pipeline-internal, opt-in | [`lstm_wire.py`](src/hanoi_air/lstm_wire.py) |
| API hardening (X-API-Key + slowapi rate limit + district/hours/fields params) | `/forecast`, `/alerts` | [`api/main.py`](api/main.py) |
| Prod stack (nginx reverse proxy + pinned tags + healthchecks) | `docker-compose.prod.yml`, `nginx.conf`, `Makefile` `make prod-up` | [`docker-compose.prod.yml`](docker-compose.prod.yml) |

## Accuracy

Backtest snapshots land at `data/processed/backtest_*.json` and render in the **📐 Độ chính xác** tab. Run any time with:

```powershell
make backtest                          # = python scripts/run_backtest.py --days 7
```

The CLI prints a markdown table comparing the heuristic forecast against a persistence baseline (the median of the prior 7-day reading window) per district, with overall RMSE / MAE / R² / MBE and an "RMSE improvement vs persistence" delta.

### Current snapshot (2026-05-12, n = 2)

| Predictor | RMSE | MAE | R² | MBE | n |
| --- | ---: | ---: | ---: | ---: | ---: |
| Forecast (T+0 vs historical reading) | 38.68 | 27.45 | -4.50 | -27.45 | 2 |
| Persistence baseline | 1.27 | 1.25 | 0.99 | -1.25 | 2 |

**Honest caveat.** With `n = 2` and no forecast-bundle archiving yet in place, this comparison pairs *today's* T+0 prediction with archived readings from *different hours* — apples to oranges. The persistence baseline (median of the prior window) trivially wins because it is essentially "yesterday's reading vs yesterday's reading." To make this number meaningful we need: (a) the worker to snapshot every forecast bundle on its 30-minute cadence into `data/processed/forecast_bundles/`, and (b) the validation to pair each archived reading with the bundle generated at its own hour. Both are tracked as Week 2 work.

> **Target (post-bundle-archiving).** RMSE PM2.5 < 15 µg/m³, R² > 0.85 on a 7-day OpenAQ backtest, with the LSTM ensemble gate enabled only where it beats the heuristic per district.

## Screenshots

Save dashboard captures to `docs/screenshots/` and reference them here:

| | |
| --- | --- |
| ![Map](docs/screenshots/01_map.png) | ![VN_AQI tab](docs/screenshots/02_vn_aqi.png) |
| ![Source pie](docs/screenshots/03_sources.png) | ![Actions tab](docs/screenshots/04_actions.png) |

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

- **Dashboard** (Streamlit): <http://localhost:8501>
- **API** (FastAPI): <http://localhost:8000> (docs at <http://localhost:8000/docs>)
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

All routes return JSON. `/health` and `/districts` are always public. `/forecast` and `/alerts` accept *either* `X-API-Key` *or* `Authorization: Bearer <jwt>` when `API_KEYS` is set in the environment, and are rate-limited per credential by slowapi.

| Method | Path | Auth | Rate limit (default) |
| --- | --- | --- | --- |
| GET | `/health` | none | unlimited |
| GET | `/districts` | none | unlimited |
| POST | `/auth/token` | `X-API-Key` (strict — no bearer fallback) | inherited from app |
| GET | `/forecast` | `X-API-Key` *or* bearer JWT | `60/minute` (`RATE_LIMIT_FORECAST`) |
| GET | `/alerts` | `X-API-Key` *or* bearer JWT | `30/minute` (`RATE_LIMIT_ALERTS`) |

### Auth modes

- **X-API-Key (default).** Set `API_KEYS=demo,pitch` in `.env`. Send `X-API-Key: demo` on each request. Zero new dependencies, fine for server-to-server.
- **JWT bearer (optional).** Set `JWT_SECRET=<random 48+ chars>` in `.env`. `POST /auth/token` with the API key returns a short-lived HS256 JWT (TTL configurable via `JWT_TTL_MINUTES`, default 60). Subsequent calls can use `Authorization: Bearer <jwt>` and the JWT subject is what slowapi sees for rate limiting. When `JWT_SECRET` is unset, `/auth/token` returns 503 and the X-API-Key path is the only option.

`/forecast` query parameters:

- `district` — district slug (e.g. `hoan_kiem`). Filters rows to this district.
- `hours` — return only the first N hour offsets (1–24).
- `hour_offset` — return only this exact hour offset (0–23). Wins over `hours`.
- `fields` — CSV allow-list to trim heavy rows, e.g. `vn_aqi,actions,source_breakdown,downwind_risk`. Minimal core fields (`district_id`, `hour_offset`, `pm25`, `aqi`, `category`, `timestamp`) are always returned.
- `district_id` — deprecated alias for `district` (kept for backwards compatibility).
- `force_refresh` — bypass the cache. Defaults to `false`.
- `use_live` — toggle live ingestion vs sample mode. Defaults to `true`.

### Example curls

```powershell
# 1. Liveness (no auth)
curl http://localhost/api/health

# 2. Full bundle for one district, next 24 h (X-API-Key path)
curl -H "X-API-Key: demo" "http://localhost/api/forecast?district=hoan_kiem&hours=24"

# 3. Lean payload for a mobile client: AQI + VN_AQI + actions only
curl -H "X-API-Key: demo" "http://localhost/api/forecast?district=hoan_kiem&hours=1&fields=vn_aqi,actions"

# 4. JWT path: mint a token, then use bearer auth for subsequent calls
TOKEN=$(curl -s -X POST -H "X-API-Key: demo" http://localhost/api/auth/token | jq -r .access_token)
curl -H "Authorization: Bearer $TOKEN" "http://localhost/api/forecast?district=hoan_kiem&hours=24"
```

## Modeling Notes

The current plume model is a pure-Python Gaussian plume approximation, designed as a pluggable MVP. It is not a regulatory AERMOD run. External AERMOD/HYSPLIT can be added behind the same dispersion interface once binaries and met/terrain data are available.

The LSTM component is implemented with PyTorch when installed, with a deterministic fallback for smoke tests. The bridge layer in [`lstm_wire.py`](src/hanoi_air/lstm_wire.py) gates the ensemble blend on per-district RMSE: if the trained LSTM beats the heuristic on the last 7-day backtest, the final prediction is `0.7 × heuristic + 0.3 × LSTM`; otherwise the heuristic alone is used. Worst case is the heuristic, never worse.

To train against the live archive once the worker has populated `data/processed/`:

```powershell
python -c "from hanoi_air.lstm_wire import train_lstm; print(train_lstm(days=30, epochs=10))"
```

This writes `models/lstm_pm25_v1.json` (metadata). When no archive exists, the call returns `{"status": "no_data"}` so the pipeline keeps running with the heuristic.

Open-Meteo/CAMS background is bias-corrected with fresh station observations when available. Station/crawl data receive quality flags such as `live_api`, `public_crawl`, `forecast_background`, and `sample`; source freshness is tracked in `.cache/source_status.json`.
