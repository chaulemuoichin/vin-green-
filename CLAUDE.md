# CLAUDE.md — Hanoi Air Forecast

> **Status: Phases 0+1+2 done (foundation + reliability + containerization).** Production-grade refactor in progress per `~/.claude/plans/l-n-k-ho-ch-rosy-whale.md`. Currently: structured logging, httpx+tenacity retries, pydantic-settings, ruff/black/mypy, atomic cache writes with filelock, per-source circuit breaker, Sentry-ready, archive retention, Dockerfile + docker-compose. 22/22 tests pass. Still missing: API auth, CI/CD, ML wiring, VN_AQI, observability endpoints. See [Production Gaps](#production-gaps).

---

## 1. What this is (60-second context)

A 24-hour AQI / PM2.5 / NO₂ forecast for **12 central districts of Hanoi**, with downwind alert generation driven by a Gaussian-plume approximation.

The pipeline blends:
- Live station readings (AQICN, OpenAQ)
- Background forecast (Open-Meteo Air Quality — free, no key)
- Weather (Open-Meteo Weather Forecast — free, no key)
- Traffic congestion proxy (Overpass road density + optional Google Maps)
- Emission sources (sample CSV; CEM API hook exists but unused)

Outputs:
- **Streamlit dashboard** ([app/streamlit_app.py](app/streamlit_app.py)) — dark glassmorphism UI, Folium map with heatmap + wind arrows, Plotly 24h chart
- **FastAPI service** ([api/main.py](api/main.py)) — `/forecast`, `/alerts`, `/districts`, `/health`
- **Celery worker** ([worker/tasks.py](worker/tasks.py)) — refreshes cache every 30 min
- **CLI** ([scripts/top5_forecast.py](scripts/top5_forecast.py)) — top-5 worst districts for tomorrow

---

## 2. Architecture map

```
                    ┌──────────────────────────────────────┐
                    │   External APIs (rate-limited)       │
                    │  AQICN · OpenAQ · Open-Meteo         │
                    │  Overpass · Google Maps · SOMO/CEM   │
                    └──────────────┬───────────────────────┘
                                   │ HTTPS (urllib.request)
                                   ▼
   ┌───────────────────────────────────────────────────────────┐
   │  src/hanoi_air/ingestion.py                                │
   │  ─ fetch_* per source, archive_raw_payload, mark_status    │
   │  ─ Cadence + freshness gating via sources.py registry      │
   └────────────┬───────────────────────────────┬──────────────┘
                │                               │
                ▼                               ▼
   ┌────────────────────────┐    ┌─────────────────────────────┐
   │ data/raw/{src}/YYYY-MM │    │ .cache/source_status.json   │
   │ archived JSON/HTML      │    │ last-success per source     │
   └────────────────────────┘    └─────────────────────────────┘
                │
                ▼
   ┌──────────────────────────────────────────────────────────┐
   │  src/hanoi_air/forecast.py — build_forecast()             │
   │  ┌───────────────────────────────────────────────────┐    │
   │  │ 1. Interpolate station readings (IDW) per district │    │
   │  │ 2. Bias-correct Open-Meteo background per district │    │
   │  │ 3. Blend: 0.55·obs + 0.45·corrected_background     │    │
   │  │ 4. Add traffic_index × diurnal × seasonal factors  │    │
   │  │ 5. Add Gaussian plume contribution (dispersion.py) │    │
   │  │ 6. Clamp + compute AQI (US-EPA-style breakpoints)  │    │
   │  └───────────────────────────────────────────────────┘    │
   └────────────────┬─────────────────────────────────────────┘
                    ▼
   ┌──────────────────────────────────────────────────────────┐
   │   cache.py — load/save_cache (JSON or Redis if URL set)   │
   └────────────────┬─────────────────────────────────────────┘
                    ▼
        ┌───────────┴───────────┐
        ▼                       ▼
   FastAPI                 Streamlit
```

---

## 3. Key files map

| File | Role | Touch when |
|---|---|---|
| [src/hanoi_air/config.py](src/hanoi_air/config.py) | `Settings` dataclass, env loading | adding a new env var |
| [src/hanoi_air/sources.py](src/hanoi_air/sources.py) | Source registry, cadence/freshness, status tracking | adding a new data source |
| [src/hanoi_air/ingestion.py](src/hanoi_air/ingestion.py) | All `fetch_*` and `parse_*` functions | new source / API change |
| [src/hanoi_air/archive.py](src/hanoi_air/archive.py) | Raw/processed file writers | changing storage layout |
| [src/hanoi_air/forecast.py](src/hanoi_air/forecast.py) | Hybrid forecast pipeline | tuning blend weights, adding features |
| [src/hanoi_air/dispersion.py](src/hanoi_air/dispersion.py) | Gaussian plume math | replacing with AERMOD/HYSPLIT |
| [src/hanoi_air/interpolation.py](src/hanoi_air/interpolation.py) | IDW / optional kriging | changing spatial interpolation |
| [src/hanoi_air/air_quality.py](src/hanoi_air/air_quality.py) | AQI breakpoints, category, health text | changing AQI scale |
| [src/hanoi_air/alerts.py](src/hanoi_air/alerts.py) | Threshold-based alert generation + webhook | alert rules / channels |
| [src/hanoi_air/viz.py](src/hanoi_air/viz.py) | Folium map (heatmap, wind, layers) | visual changes |
| [src/hanoi_air/model.py](src/hanoi_air/model.py) | LSTM scaffold (currently UNUSED by forecast) | wiring ML in |
| [src/hanoi_air/schemas.py](src/hanoi_air/schemas.py) | Frozen dataclasses for all entities | adding new fields |
| [app/streamlit_app.py](app/streamlit_app.py) | Dashboard with CSS theme + Plotly | UI changes |
| [data/sample/districts.csv](data/sample/districts.csv) | **The 12 central districts** (canonical list) | changing geographic scope |
| [tests/](tests/) | pytest suite — **currently broken**, see below | adding tests |

---

## 4. Districts (canonical 12)

We dropped the 19 outer/rural districts (Sơn Tây, Ba Vì, etc.) on 2026-05-11. Current scope is the **12 inner urban districts** only:

| ID | Vietnamese | Lat | Lon | Notes |
|---|---|---|---|---|
| `ba_dinh` | Ba Đình | 21.0369 | 105.8347 | Government core |
| `hoan_kiem` | Hoàn Kiếm | 21.0288 | 105.8522 | Old Quarter, smallest district |
| `tay_ho` | Tây Hồ | 21.0682 | 105.8236 | West Lake area |
| `long_bien` | Long Biên | 21.0449 | 105.8901 | East of Red River, logistics |
| `cau_giay` | Cầu Giấy | 21.0362 | 105.7906 | Tech corridor |
| `dong_da` | Đống Đa | 21.0181 | 105.8295 | Densest district |
| `hai_ba_trung` | Hai Bà Trưng | 21.0069 | 105.8577 | Mixed residential + industrial |
| `hoang_mai` | Hoàng Mai | 20.9749 | 105.8677 | South Hanoi |
| `thanh_xuan` | Thanh Xuân | 20.9938 | 105.8025 | Major traffic corridor |
| `nam_tu_liem` | Nam Từ Liêm | 21.0128 | 105.7604 | West, new developments |
| `bac_tu_liem` | Bắc Từ Liêm | 21.0636 | 105.7608 | Northwest, **highest forecast AQI** in sample |
| `ha_dong` | Hà Đông | 20.9712 | 105.7788 | Southwest |

> **Hardcoded references** to specific district IDs exist in [forecast.py](src/hanoi_air/forecast.py) (`_receptor_for_district`, `_hotspot`). When adding/removing a district, update these dicts too.

---

## 5. Data source priority (live mode)

`load_air_readings()` calls fetchers in this order and **stops at first non-empty result** (with falls-through to sample):

1. **AQICN** (`fetch_aqicn_readings`) — if `AQICN_TOKEN` set: per-district geo query. Else: 4 fixed Hanoi city feeds using the documented `demo` fallback token (limited reliability — not for prod).
2. **OpenAQ** (`fetch_openaq_readings`) — uses `/v3/locations?bbox=...` then per-sensor `/v3/sensors/{id}/measurements?limit=1`. **NOT** `/v3/measurements` — that endpoint returns 404 in v3.
3. **SOMO crawler** — public site, polite delay, no auth.
4. **CEM crawler** — government site.
5. **OpenWeather** — fallback only.
6. Sample CSVs in `data/sample/`.

Open-Meteo (`fetch_open_meteo_weather_forecast`, `fetch_open_meteo_air_forecast`) is **always** called from `build_forecast()` regardless — it provides the background CAMS-equivalent that gets bias-corrected by station readings.

### Cadence (in `sources.py`)
| Source | Cadence | Freshness window |
|---|---|---|
| `open_meteo_weather` | 30 min | 90 min |
| `open_meteo_air` | 30 min | 120 min |
| `aqicn` | 30 min | 120 min |
| `openaq` | 60 min | 180 min |
| `somo_crawler` | 30 min | 180 min |
| `cem_crawler` | 60 min | 240 min |
| `overpass_roads` | 30 days | 31 days |

`should_fetch_source()` checks `last_success` against cadence — within the window, fetchers return processed cached data instead of re-hitting the API.

---

## 6. API integration quirks (learned the hard way)

### AQICN
- Free token: register email at https://aqicn.org/api/. Token works without rate limits at 30-min cadence.
- Geo query `/feed/geo:{lat};{lon}/` returns the **nearest** station, which means querying 12 district centroids may return only **2-3 unique stations** (we observed Tây Hồ + Long Biên repeated). This is a data sparsity issue, not a bug.
- The `demo` token works for fixed city feeds (`/feed/hanoi/`) but should not be relied on in production.

### OpenAQ v3
- **`/v3/measurements` endpoint returns 404** — it does not exist in v3. Use `/v3/sensors/{id}/measurements?limit=1` per sensor.
- The `/v3/locations` endpoint returns sensor metadata but no `latest` field — must call per-sensor.
- Free key from https://explore.openaq.org/register, 10k req/month.
- Many Hanoi sensors are historical (last data 2016) — filter by `datetimeLast`.

### Open-Meteo
- Truly free, no key, no auth. ~10k calls/day soft limit per IP.
- Air Quality endpoint accepts multi-point batch: comma-separated `latitude=&longitude=` for all 12 districts in one call.

### Google Maps Distance Matrix (optional)
- Requires billing-enabled GCP project ($300 free credit).
- Used only for fine-grained traffic congestion proxy — **the rest of the pipeline works without it**.

### SOMO / CEM crawlers
- Polite-by-default (`USER_AGENT` set, 0.2s sleep between requests).
- **Fragile**: HTML structure can change without notice. Parsers in `parse_somo_html` / `parse_cem_html` use regex on flattened text.
- **Disable in CI** (`ENABLE_PUBLIC_CRAWL=false`) to avoid flaky tests.

---

## 7. Setup

### Quick start with Docker (Recommended)

```powershell
# Copy and configure environment
cp .env.example .env
# Edit .env with AQICN_TOKEN, OPENAQ_API_KEY (free signup links in the file)

# Start all services (Redis, API, Worker, Dashboard)
make up

# View logs
make logs

# Stop services
make down
```

**Endpoints:**
- Dashboard (Streamlit): http://localhost:8501
- API (FastAPI): http://localhost:8000
- API docs: http://localhost:8000/docs
- Redis: redis:6379

### Local development (no Docker)

```powershell
# Create virtual environment
python -m venv .venv
.venv\Scripts\Activate.ps1
python -m pip install -r requirements.txt

# Copy & fill keys
cp .env.example .env
# Edit .env with AQICN_TOKEN, OPENAQ_API_KEY (free signup links in the file)

# Start local development (Streamlit + API + Worker in separate terminals)
make dev
```

Or run individually:

```powershell
# Terminal 1: Streamlit dashboard
streamlit run app/streamlit_app.py

# Terminal 2: FastAPI server
uvicorn api.main:app --reload --port 8000

# Terminal 3: Celery worker (requires local Redis)
celery -A worker.tasks worker -B --loglevel=info
```

### Makefile commands

```powershell
make help          # Show all available commands
make up            # Start Docker services
make down          # Stop Docker services
make logs          # Tail all service logs
make test          # Run pytest suite
make lint          # Run ruff linter
make format        # Format with black
make type-check    # Run mypy strict type checking
make quality       # Run all linting + formatting + type-check
```

---

## 8. Forecast algorithm (current — heuristic, not ML)

`build_forecast()` produces one row per (district × hour) for the next 24 hours:

```
pm25_final = clamp(
    blend(observed_interpolated, bias_corrected_background) ×
    diurnal_factor(hour) × seasonal_factor(month) × ventilation_factor(wind, humidity)
    + traffic_index × traffic_hour_factor(hour)
    + 0.46 × plume_pm25_from_sources
, 4.0, 220.0)
```

Where:
- `blend = 0.55·obs + 0.45·corrected_bg` if both available, else just obs
- `bias = mean(station_obs[t=0] - background[t=0])` per district, capped at ±35 µg/m³
- `diurnal_factor` — gaussian peaks at 8h and 18h
- `seasonal_factor` — winter +18%, monsoon -6%
- `ventilation_factor` — penalizes low wind + high humidity
- `plume` — Gaussian dispersion from `factories.csv` sources

**Confidence band**: `uncertainty = max(12, 0.2·aqi, 8 + 0.45·h_offset + 0.25·plume_pm25)` — purely heuristic, NOT a real prediction interval.

> The `LSTMForecaster` class in [model.py](src/hanoi_air/model.py) exists but is **not called** by the forecast pipeline. It's training scaffolding only.

---

## 9. Caching & reliability

### Cache layers

| Layer | Location | TTL | Reset |
|---|---|---|---|
| Forecast bundle | `.cache/forecast_cache.json` or Redis | 1800s | `force_refresh=True` |
| Source-specific (weather, air bg, road density) | same | per-source cadence | n/a |
| Source status + circuit breaker state | `.cache/source_status.json` | n/a | manual delete |
| Streamlit `@st.cache_data` | in-process | 1800s | UI button or rerun |

**Atomic file writes (Phase 1)**: file-backed cache writes use `tempfile + os.replace` under a `filelock`, so multiple workers cannot tear each other's writes. The read-modify-write happens under the lock — siblings never get lost. Test coverage: `tests/test_cache_concurrency.py` (8 workers × 1 key each).

**Redis precedence**: If `REDIS_URL` is set, all reads/writes go to Redis. Local `.cache/*.json` files become stale and confusing — delete them to avoid debugging ghosts.

### Circuit breaker (Phase 1)

Each `fetch_*` function in [ingestion.py](src/hanoi_air/ingestion.py) is wrapped with `@guard_source("name", fallback=[])` from [retry.py](src/hanoi_air/retry.py):

- After **3 consecutive failures**, the breaker opens for **5 minutes**.
- While open, calls return the fallback (`[]`) without hitting the API, so we don't waste timeouts on a known-dead endpoint.
- Any success resets the failure counter and closes the breaker.

State is persisted in `source_status.json` under keys `consecutive_failures` and `circuit_open_until` (epoch seconds). Inspect by reading the file or calling `is_circuit_open(source_name)`.

**Per-request retries** (separate from the breaker) live in [http.py](src/hanoi_air/http.py): 3 retries with exponential backoff via `tenacity`, on transient errors (`TimeoutException`, `ConnectError`, `RemoteProtocolError`, `ReadError`). 5xx responses do **not** retry (treated as the API saying "no" rather than a transient blip).

### Sentry (opt-in)

Set `SENTRY_DSN` env var to enable. All three entrypoints (api/worker/dashboard) call `init_sentry(service="...")` at import time — safe to leave unset for dev. See [observability.py](src/hanoi_air/observability.py).

### Archive retention

`scripts/cleanup_raw_archive.py` deletes `data/raw/{source}/YYYY-MM-DD/` older than 7 days. Run daily via Celery beat (`worker.tasks.cleanup_archive`). Use `--dry-run` to preview, `--include-processed` to also rotate `data/processed/` (90-day default).

---

## 10. Coding conventions

### Style
- **Python 3.10+** features assumed (`X | None` syntax, PEP 604).
- `from __future__ import annotations` at the top of every module.
- `@dataclass(frozen=True)` for all entities in [schemas.py](src/hanoi_air/schemas.py) — they pass through cache as JSON, so freezing prevents mutation bugs.
- Functions accept `settings: Optional[Settings] = None` and `settings = settings or get_settings()` — makes testing easy.
- All timestamps are stored as `datetime` with `tzinfo=timezone.utc`. Local-time math (Hanoi = UTC+7) lives in `_hanoi_hour` helper.

### Don't
- ❌ Don't add `print()` — use the structured logger (`from .logging_setup import get_logger; logger = get_logger(__name__)`).
- ❌ Don't catch `Exception` and `continue` silently. Always log with `logger.warning(...)` or `logger.debug(...)` and include the exception via `exc=exc`. Phase 0 cleaned this up across `ingestion.py`/`cache.py`/`alerts.py`/`archive.py`/`sources.py` — don't reintroduce.
- ❌ Don't use `urllib.request` for new external calls — use `hanoi_air.http.http_get_json` / `http_get_text` (retries, connection pool, structured logs).
- ❌ Don't read env vars with `os.getenv` in business logic — extend `Settings` in [config.py](src/hanoi_air/config.py) instead.
- ❌ Don't add new hardcoded district IDs without checking [forecast.py](src/hanoi_air/forecast.py) `_receptor_for_district` and `_hotspot`.
- ❌ Don't commit `.env` (it's in `.gitignore`).
- ❌ Don't change the AQI breakpoints in [air_quality.py](src/hanoi_air/air_quality.py) without coordination — alerts and UI both depend on the scale.

### Do
- ✅ When adding a new source: register in `SOURCE_REGISTRY` ([sources.py](src/hanoi_air/sources.py)) FIRST, then write `fetch_*` and `parse_*`.
- ✅ Archive raw payloads via `archive_raw_payload()` — useful for backtesting parser changes.
- ✅ Use `mark_source_status()` after every fetch attempt — populates the source health UI.
- ✅ For new geographic data: use the `nearest_district()` helper rather than custom matching.
- ✅ Bind a module-scoped logger: `logger = get_logger(__name__)` at the top of every module that needs logging.
- ✅ Run `ruff check`, `black`, `mypy` before commit. Pre-commit hook does this automatically when installed: `pre-commit install`.

---

## 11. Testing & quality gates

### Run the full suite

```powershell
python -m pytest                                # 17 tests, ~3s
python -m ruff check src/ tests/ api/ worker/   # linting
python -m black --check src/ tests/ api/ worker/  # formatting
python -m mypy src/hanoi_air                    # type check (strict)
pre-commit run --all-files                      # runs everything
```

### What's covered (Phase 0 baseline)
- AQI math, IDW interpolation, wind components, Gaussian plume direction
- LSTM smoke training + prediction shape
- Forecast bundle structure (12-district shape), alert threshold edges, top-5 report
- FastAPI `/health`, `/districts`, `/forecast` smoke (12 districts)
- Free-source parsers (Open-Meteo, OpenAQ legacy, SOMO, Overpass)
- httpx layer live-tested against AQICN/OpenAQ — passes with real keys

### What's NOT covered (gaps for later phases)
- Live API integration via VCR cassettes (Phase 1 will add tenacity retry tests)
- OpenAQ v3 sensor-per-call fetch flow happy path
- Cache eviction / TTL expiry (Phase 1: concurrent write tests)
- Crawler resilience to HTML changes
- Bias correction math (only tested implicitly via bundle shape)
- ML model accuracy (Phase 6: backtest framework will add MAE/RMSE assertions)

---

## 12. Production Gaps

> The system **looks** production-grade in the dashboard. Internally there are several blocking issues for real deployment.

### 🔴 Critical (must fix before any real traffic)

| Gap | Status | Fix |
|---|---|---|
| ~~**No logging** at all~~ | ✅ **Phase 0 done** | loguru in [logging_setup.py](src/hanoi_air/logging_setup.py), auto-configured on import |
| ~~**Silent error swallowing**~~ | ✅ **Phase 0 done** | All `except Exception:` blocks now log via `logger.warning/debug` with exc context |
| ~~**`urllib.request` with no retry**~~ | ✅ **Phase 0 done** | [http.py](src/hanoi_air/http.py): httpx + tenacity (3 retries, exp backoff) |
| ~~**No structured config**~~ | ✅ **Phase 0 done** | [config.py](src/hanoi_air/config.py) uses pydantic-settings with validators + secret hiding |
| ~~**Tests broken**~~ | ✅ **Phase 0 done** | 30→12 district counts updated, 17/17 pass |
| **No API auth / rate limiting** | ⏳ Phase 3 | API key middleware + `slowapi` |
| ~~**Cache file race condition**~~ | ✅ **Phase 1 done** | filelock + tempfile + os.replace ([cache.py](src/hanoi_air/cache.py)); concurrency test in [tests/test_cache_concurrency.py](tests/test_cache_concurrency.py) |
| ~~**No retry / circuit breaker**~~ | ✅ **Phase 1 done** | httpx retry layer + [retry.py](src/hanoi_air/retry.py) `guard_source` breaker (3 failures → 5min cooldown) |
| ~~**No error tracking**~~ | ✅ **Phase 1 done** | Sentry-ready ([observability.py](src/hanoi_air/observability.py)); opt-in via `SENTRY_DSN` |
| ~~**Raw archive grows unbounded**~~ | ✅ **Phase 1 done** | [scripts/cleanup_raw_archive.py](scripts/cleanup_raw_archive.py) + daily Celery beat task |
| **Tests don't run live API code** | ⏳ Phase 3 | VCR cassettes for AQICN/OpenAQ |

### 🟡 High priority

| Gap | Status | Fix |
|---|---|---|
| ~~**No type checker**~~ | ✅ **Phase 0 done** | `mypy --strict` configured in `pyproject.toml` (currently scoped to `src/hanoi_air/`) |
| ~~**No linter**~~ | ✅ **Phase 0 done** | ruff + black + pre-commit-config.yaml; bumped to ruff 0.5+ |
| **No CI/CD** | ⏳ Phase 4 | GitHub Actions: lint + test + type-check on PR |
| **AQI scale ambiguity** | uses US EPA, app is in Vietnamese | Document clearly, or implement VN_AQI per QCVN 06:2022/BTNMT |
| **No backtest framework** | forecast model has no evaluation | Add `scripts/backtest.py` against archived processed data |
| **LSTM unused** | `model.py` is scaffolding | Either wire it in or delete it |
| **No model versioning** | n/a | When ML lands, use MLflow or simple `models/{version}/` |

### 🟢 Production polish

| Gap | Where | Fix |
|---|---|---|
| ~~**No Dockerfile**~~ | ✅ **Phase 2 done** | Multi-stage build ([Dockerfile](Dockerfile)), slim base, connection pooling |
| ~~**No docker-compose**~~ | ✅ **Phase 2 done** | [docker-compose.yml](docker-compose.yml) brings up Redis + worker + api + dashboard with health checks |
| **No metrics** | n/a | `/metrics` Prometheus endpoint, OpenTelemetry traces |
| ~~**No Sentry**~~ | ✅ **Phase 1 done** | `init_sentry(service=...)` in api/worker/dashboard |
| **Streamlit not production-ideal** | latency, no SSR | Long-term: rewrite frontend in Next.js + Mapbox |
| ~~**Raw archive grows unbounded**~~ | ✅ **Phase 1 done** | cleanup_raw_archive.py + Celery daily beat task; 7-day raw / 90-day processed defaults |
| **No data quality dashboard** | source status exists but not exposed | Add `/sources` endpoint + UI panel showing freshness |
| **No mobile responsive layout** | Streamlit limits | Test on viewport <768px, hide heavy panels |

### Quick-win sequence (1 week sprint)

1. Day 1: Fix broken tests, add `ruff` + `black`, add `loguru` and replace silent exceptions
2. Day 2: Migrate `urllib` → `httpx` with retry. Add `pydantic-settings`.
3. Day 3: Add GitHub Actions (lint + test). Add Dockerfile + docker-compose.
4. Day 4: Add `/sources` endpoint + Sentry. Atomic cache file writes.
5. Day 5: Add API key middleware on FastAPI. Document API in OpenAPI.

---

## 13. Common tasks (cookbook)

### "Add a new district"
1. Append row to [data/sample/districts.csv](data/sample/districts.csv).
2. If urban: optionally add to `_hotspot` dict in [forecast.py](src/hanoi_air/forecast.py).
3. Add sample station row to [data/sample/stations_current.csv](data/sample/stations_current.csv) so demo mode shows real data.
4. Run tests — the `district_count` assertion will need updating.

### "Add a new air quality data source"
1. Define entry in `SOURCE_REGISTRY` ([sources.py](src/hanoi_air/sources.py)) with cadence/freshness.
2. Add `parse_<source>_payload()` returning `List[AirReading]`.
3. Add `fetch_<source>_readings(settings)` with `should_fetch_source()` gate + `archive_raw_payload()` + `mark_source_status()`.
4. Wire into `load_air_readings()` priority order.
5. Add sample fixture in `data/sample/` and parser test in `tests/test_free_sources.py`.

### "Change the blend weights"
- [forecast.py](src/hanoi_air/forecast.py) line ~78: `0.55 * obs_pm25 + 0.45 * corrected_pm25`. These are tuned by eye, not learned. Run a backtest (TODO: build one) before changing.

### "Add a new alert channel"
- [alerts.py](src/hanoi_air/alerts.py) `post_alerts()` currently only does HTTP POST to a webhook. Add a separate function for Slack/Telegram/SMS rather than overloading webhook.

### "Debug 'why is the heatmap showing 12 separate blobs'"
- HeatMap `radius` was too large vs grid spacing. Currently `radius=14, blur=18` in [viz.py](src/hanoi_air/viz.py). If you increase grid_size in `_interpolated_heatmap_points`, also decrease radius to maintain visual smoothness.

### "Live data shows AQICN with only 2 districts"
- Not a bug. AQICN's geo query returns the nearest **physical** station. With ~3 active monitors in Hanoi, all 12 district queries map to a small set of stations. OpenAQ fills this gap better (currently returning 78 readings).

---

## 14. Glossary

- **AQI** — Air Quality Index (operational, US-EPA-style here, not VN_AQI)
- **CAMS** — Copernicus Atmosphere Monitoring Service (background forecast)
- **CEM** — Cục Quản lý Môi trường VN (Vietnam Environmental Administration)
- **CEMS** — Continuous Emissions Monitoring System (factory stacks)
- **IDW** — Inverse Distance Weighting (spatial interpolation)
- **Plume** — Modeled downwind dispersion from a point source
- **SOMO** — Sở Tài nguyên Môi trường Hà Nội public station page
- **VN_AQI** — Vietnam official AQI per QCVN 06:2022/BTNMT (NOT what we compute)

---

## 15. When working in this repo with an AI agent

- **Don't trust the README's "30 districts"** — it predates the 2026-05-11 reduction. The canonical list is in [data/sample/districts.csv](data/sample/districts.csv) and Section 4 above.
- **Tests are currently broken** post-reduction. Fix them before adding new tests.
- **The LSTM is unused.** If asked "improve the model", that's the obvious first wire-up — but also evaluate whether the heuristic in `forecast.py` is the actual bottleneck.
- **Heuristic constants are tuned for sample data**, not validated. Don't take `0.55`, `0.46`, `0.18`, etc. as truth.
- **Streamlit caching + Folium re-render quirks**: `st_folium(key=...)` must include any state that changes the map (hour, district). See `app/streamlit_app.py` line ~250.
- **Vietnamese text in source files** — use UTF-8. On Windows, `sys.stdout.reconfigure(encoding='utf-8')` for scripts.
- **Don't add files in `data/raw/` to git** — they're generated and gitignored.

---

_Last reviewed: 2026-05-12 (Phases 0+1+2 complete: foundation tooling + reliability + containerization). Bump this date when making structural changes._
