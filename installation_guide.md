# Installation Guide — Pollution Episode Explanation Engine
# Hướng dẫn Cài đặt — Hệ thống Giải thích Ô nhiễm Không khí Hà Nội

**Platform tested:** Windows 11 / macOS / Linux (Python 3.10+)  
**Time to complete:** ~20 minutes  
**What you get:** All APIs connected, all scripts runnable, ready to query live fire data.

---

## Quick Status — What's Already Done

| Step | Status | Done by |
|------|--------|---------|
| FIRMS API key | **Done** | Markie |
| WAQI token | **Done** | Markie |
| CAMS/CDS API key | **Done** | Markie |
| Python packages | You install | This guide |
| Google Earth Engine auth | You do | This guide (5 min) |
| CAMS Terms of Use | You accept | This guide (2 min) |
| HYSPLIT web | Nothing to install | Use browser |

---

## Step 1 — Python Environment

You need Python 3.10 or higher. Check:
```
python --version
```

Install all packages:
```
python -m pip install pandas requests geopy earthengine-api "cdsapi>=0.7.7" netCDF4 xarray
```

Verify the install:
```python
python -c "import pandas, requests, geopy, ee, cdsapi; print('All packages OK')"
```

---

## Step 2 — FIRMS API (Already Done — Just Verify)

FIRMS = NASA fire detection API. Key already obtained.

Test the key in your browser (paste this URL):
```
https://firms.modaps.eosdis.nasa.gov/mapserver/mapkey_status/?MAP_KEY=574c47a834cae0aead0af0ab21e2ba6b
```

Expected response:
```json
{"transaction_limit": 5000, "current_transactions": 0, "transaction_interval": "10 minutes"}
```

Pull live fire data for the Hanoi region (last 3 days):
```
https://firms.modaps.eosdis.nasa.gov/api/area/csv/574c47a834cae0aead0af0ab21e2ba6b/VIIRS_NOAA20_NRT/102.0,18.3,109.7,23.7/3
```

This returns a CSV — open in browser or read with `pd.read_csv(url)` directly.

---

## Step 3 — WAQI Token (Already Done)

WAQI = real-time AQI stations. Token already obtained.

**Token:** `cab9db60dd861a68c54b8fd73f2c17f7c5517f0a`

Test it:
```
https://api.waqi.info/feed/hanoi/?token=cab9db60dd861a68c54b8fd73f2c17f7c5517f0a
```

Expected: `{"status": "ok", "data": {"aqi": ...}}`

**Known Hanoi station UIDs:**
- `@8641` — US Embassy (sometimes offline)
- `@8688` — UN International School (reliable)
- `@1583` — Hanoi city aggregate

---

## Step 4 — Google Earth Engine (5 minutes)

GEE is needed for Sentinel-5P satellite data (NO2, SO2, CO, aerosol index).

**4a. Project setup**

The shared project `these-streets` (Google Cloud #288828471914) is already configured in the code.

**Option A — use the shared project (ask Markie to add you):**  
Markie needs to add your Google account at `https://console.cloud.google.com/iam-admin/iam?project=these-streets`. Then skip to Step 4b.

**Option B — create your own free project (2 min, no coordination needed):**
1. Go to `https://code.earthengine.google.com`
2. Sign in with your Google account
3. Click "Register a new project" → "Unpaid usage" → "Academia / Research"
4. Copy the **Project ID** it gives you
5. In `explore_sentinel5p.py` line 16, set `GEE_PROJECT = 'your-project-id'`

**4b. Authenticate on your machine**

Run this in terminal (opens a browser for Google login):
```
earthengine authenticate
```

Follow the prompts. After authenticating, initialize with your project ID:
```python
import ee
ee.Initialize(project='these-streets')  # paste your project ID here
```

**4c. Test it**
```python
import ee
ee.Initialize(project='these-streets')

col = ee.ImageCollection('COPERNICUS/S5P/NRTI/L3_NO2').limit(1)
print(col.size().getInfo())  # should print: 1
print("GEE OK")
```

**4d. Check the script**

`explore_sentinel5p.py` line 16 is already set to the shared project:
```python
GEE_PROJECT = 'these-streets'  # already set — only change if using Option B above
```

---

## Step 5 — CAMS Copernicus (2 minutes)

CAMS = global smoke/aerosol forecast. Key is already configured in `~/.cdsapirc`.

**5a. Verify the config file exists**

Windows:
```
type %USERPROFILE%\.cdsapirc
```

macOS/Linux:
```
cat ~/.cdsapirc
```

Expected output:
```
url: https://cds.climate.copernicus.eu/api
key: f7db20f4-5fd9-42d2-9f7b-d729231dc2f7
```

If the file is missing, create it manually with that content.

**5b. Accept Terms of Use (required before first download)**

1. Go to: `https://cds.climate.copernicus.eu/datasets/cams-global-atmospheric-composition-forecasts`
2. Log in with the Copernicus account (email: `cheees2309@gmail.com`)
3. Scroll to the bottom of the page
4. Click **"Accept Terms"** or **"Accept licence"**

Without this step, the API will reject your download requests.

**5c. Test it**
```python
import cdsapi
c = cdsapi.Client()
print("CAMS connection OK — key loaded from ~/.cdsapirc")
```

---

## Step 6 — Open-Meteo & NASA POWER (No Setup Needed)

Both are free and require no API key. Just call them:

```python
import requests

# Open-Meteo — test
r = requests.get('https://api.open-meteo.com/v1/forecast', params={
    'latitude': 21.03, 'longitude': 105.85,
    'hourly': 'wind_speed_850hPa', 'forecast_days': 1
})
print("Open-Meteo OK:", r.status_code)

# NASA POWER — test
r = requests.get('https://power.larc.nasa.gov/api/temporal/hourly/point', params={
    'parameters': 'WS10M', 'community': 'RE',
    'longitude': 103.5, 'latitude': 20.5,
    'start': '20240301', 'end': '20240301', 'format': 'JSON'
})
print("NASA POWER OK:", r.status_code)
```

---

## Step 7 — HYSPLIT (No Install — Use Web)

HYSPLIT = trajectory model. Use the NOAA web interface, no local install needed.

**Web interface:** `https://www.ready.noaa.gov/HYSPLIT_traj.php`

**How to run a trajectory:**
1. Select **FORWARD** trajectory
2. Met data: **GDAS 0.5°** (auto-selected)
3. Duration: **72 hours**
4. Start location: paste fire `latitude` and `longitude` from FIRMS
5. Start time: convert FIRMS `acq_date` + `acq_time` to UTC (acq_time is already UTC)
6. Start heights: enter three values: `500`, `1000`, `1500` (meters AGL)
7. Run → download the **tdump** file

**Parse the output:**
```python
# Use the existing parser in explore_hysplit.py
from explore_hysplit import parse_tdump, check_arrival

df = parse_tdump('your_downloaded_tdump.txt')
df, arrivals = check_arrival(df)
```

---

## Step 8 — OpenAQ (No Setup — Rate Limited)

Free API, no auth for basic queries. Just be gentle with request rate.

```python
import requests

r = requests.get('https://api.openaq.gov/v3/locations', params={
    'city': 'Hanoi', 'country_id': 'VN', 'limit': 20
}, headers={'Accept': 'application/json'})

stations = r.json()['results']
for s in stations:
    print(s['id'], s['name'])
```

If you get 429 (rate limit), wait a few seconds and retry.

---

## Step 9 — Run the Explore Scripts

Run in this order (each validates one data source):

```bash
# 1. Fire data (FIRMS — VIIRS + MODIS)
python testing.py

# 2. Wind + air quality forecast (Open-Meteo)
python explore_openmeteo.py

# 3. Ground truth AQI (WAQI + OpenAQ)
python explore_openaq_waqi.py

# 4. Satellite chemical signature (Sentinel-5P via GEE — needs Step 4 done first)
python explore_sentinel5p.py

# 5. Trajectory parser test (HYSPLIT synthetic data — no real tdump needed)
python explore_hysplit.py
```

---

## All Credentials in One Place

| Service | Key / Token / Config |
|---------|---------------------|
| FIRMS MAP_KEY | `574c47a834cae0aead0af0ab21e2ba6b` |
| WAQI Token | `cab9db60dd861a68c54b8fd73f2c17f7c5517f0a` |
| CAMS API Key | `f7db20f4-5fd9-42d2-9f7b-d729231dc2f7` |
| CAMS API URL | `https://cds.climate.copernicus.eu/api` |
| GEE Project ID | `these-streets` (shared) — or create your own free project (see Step 4a) |
| Google Cloud API Key | `AIzaSyBFxTUEDoNdY6U3_AYKS6CYm2D72Asb9TE` |

---

## Troubleshooting

**`ModuleNotFoundError: No module named 'ee'`**
```
python -m pip install earthengine-api
```

**`ee.ee_exception.EEException: Please authorize access to your Earth Engine account`**
```
earthengine authenticate
```

**`cdsapi.api.AdsAPIException: 403 Forbidden`**  
→ You haven't accepted the CAMS Terms of Use. Do Step 5b.

**`ConnectionError: getaddrinfo failed`**  
→ Network blocked in this environment (sandbox). Run scripts locally on your machine, not inside Claude Code's sandbox.

**FIRMS returns 0 rows**  
→ Try increasing `DAYS` to 7. During non-burning season there may be few fires in the bbox.

**WAQI returns `{"status": "error", "data": "Unknown station"}`**  
→ Use `/feed/geo:21.03;105.85/?token={TOKEN}` (coordinate-based) instead of city name.

---

## Bounding Box Reference

All queries use this box (covers fires that can realistically reach Hanoi in 72h):

```
West:  102.0°E
South: 18.3°N
East:  109.7°E
North: 23.7°N
```

Hanoi coordinates: `21.03°N, 105.85°E`
