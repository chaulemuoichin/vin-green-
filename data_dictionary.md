# Data Dictionary — Pollution Episode Explanation Engine
# Từ điển dữ liệu — Hệ thống Giải thích Ô nhiễm Không khí Hà Nội

**Pipeline:** FIRMS → Sentinel-5P → Open-Meteo → HYSPLIT → OpenAQ/WAQI  
**Goal:** Satellite detects upstream fire → model traces smoke trajectory to Hanoi → deliver "what, where, when it arrives, how bad, when it clears" card before pollution hits.

> **How to read this doc:**  
> Field names stay in English (direct 1-to-1 mapping to code). Explanations are bilingual.  
> Sections marked **DÙNG CHO TÍNH TOÁN** = fields your math/model actually needs.  
> "Live snapshot" boxes = real data pulled 2026-05-11 from this exact pipeline.

---

## API Keys & Auth Status

| Source | Auth | Status | Key/Token |
|--------|------|--------|-----------|
| FIRMS | MAP_KEY | **Ready** | `574c47a834cae0aead0af0ab21e2ba6b` |
| Open-Meteo | None needed | **Ready** | — |
| NASA POWER | None needed | **Ready** | — |
| WAQI | Token | **Ready** | `cab9db60dd861a68c54b8fd73f2c17f7c5517f0a` |
| OpenAQ | None (basic) | **Ready** | — |
| Google Earth Engine | `earthengine authenticate` + project ID | **Ready** | Project ID: `these-streets` (project #288828471914) · API key: `AIzaSyBFxTUEDoNdY6U3_AYKS6CYm2D72Asb9TE` |
| CAMS/Copernicus | cdsapi config | **Ready** — key in `~/.cdsapirc` | Accept ToU at dataset page first |
| HYSPLIT web | None needed | **Ready** | ready.noaa.gov/HYSPLIT_traj.php |

---

## 1. FIRMS — NASA Fire Information for Resource Management System

**What it does:** Detects active fires from satellite thermal imagery. Gives you GPS coordinates, fire intensity, and timestamp — the starting point for every HYSPLIT trajectory.

**Sensors available:**

| Sensor | Endpoint key | Resolution | Passes/day | Use |
|--------|-------------|-----------|-----------|-----|
| VIIRS NOAA-20 | `VIIRS_NOAA20_NRT` | **375m** | 2 | **Primary** |
| VIIRS Suomi-NPP | `VIIRS_SNPP_NRT` | 375m | 2 | Secondary cross-check |
| MODIS (Terra+Aqua) | `MODIS_NRT` | 1km | 4 | Historical cross-check |

**Endpoint pattern:**
```
https://firms.modaps.eosdis.nasa.gov/api/area/csv/{MAP_KEY}/{SENSOR}/{west},{south},{east},{north}/{days}
```

**Live example (use this URL directly in browser or code):**
```
https://firms.modaps.eosdis.nasa.gov/api/area/csv/574c47a834cae0aead0af0ab21e2ba6b/VIIRS_NOAA20_NRT/102.0,18.3,109.7,23.7/3
```

---

### 1a. VIIRS (NOAA-20 & Suomi-NPP) — Primary Fire Source

> **Verified from real API pull (2026-05-09 → 2026-05-11):**  
> NOAA-20: 56 detections. Suomi-NPP: 41 detections. Max FRP: 328 MW (Laos border ~21.1°N, 102.5°E).

**Actual columns returned by API** (verified from live data — no `type` column in NRT product):

| Column | Type | Unit | Real range (live) | Use |
|--------|------|------|-------------------|-----|
| `latitude` | float | ° decimal | 18.3 – 23.7 | **HYSPLIT source point** |
| `longitude` | float | ° decimal | 102.0 – 109.7 | **HYSPLIT source point** |
| `frp` | float | MW | 0.85 – 328 MW (mean: 60 MW) | **Proxy for smoke emission intensity. >50 MW = worth running HYSPLIT.** |
| `bright_ti4` | float | Kelvin | 208 – 357 K | Secondary intensity signal. >400K = very intense fire. |
| `bright_ti5` | float | Kelvin | ~270 – 295 K | Background thermal reference. |
| `acq_date` | string | YYYY-MM-DD | 2026-05-09 → 2026-05-11 | **HYSPLIT start date** |
| `acq_time` | int | HHMM | 542 → 2359 | **HYSPLIT start time (UTC). e.g., `0542` = 05:42 UTC = 12:42 Hanoi.** |
| `confidence` | string | l/n/h | n=44, l=12 (in live sample) | **Filter: keep `n` and `h` only.** `l` = too many false positives. |
| `daynight` | string | D/N | D=51, N=5 | D = daytime agricultural burn. N = charcoal kiln, industry. |
| `satellite` | string | — | `N20` or `N` | N20=NOAA-20, N=Suomi-NPP |
| `instrument` | string | — | VIIRS | Always VIIRS. |
| `scan` / `track` | float | km | 0.375 – 1.6 | Pixel size. Larger off-nadir. Not needed for analysis. |
| `version` | string | — | 2.0NRT | Product version. Ignore. |

> **Important correction from real data:** The `type` field (0=vegetation, 1=volcano, etc.) does NOT appear in the NRT product. Filter on `confidence` and `frp` only.

**Filter recipe (Python):**
```python
# VIIRS filter — use this exact code
df_clean = df[
    df['confidence'].isin(['n', 'h']) &  # nominal + high only
    (df['frp'] > 0)                       # drop zero-frp anomalies
]
```

**Convert timestamp for HYSPLIT:**
```python
import pandas as pd

df['acq_time_str'] = df['acq_time'].astype(str).str.zfill(4)
df['hour_utc']   = df['acq_time_str'].str[:2].astype(int)
df['minute_utc'] = df['acq_time_str'].str[2:].astype(int)
df['ts_utc'] = pd.to_datetime(df['acq_date'].astype(str) + ' ' +
                               df['acq_time_str'].str[:2] + ':' +
                               df['acq_time_str'].str[2:], utc=True)
df['ts_hanoi'] = df['ts_utc'] + pd.Timedelta(hours=7)  # UTC+7
```

---

### 1b. MODIS NRT — Cross-validation Only

> **Verified from real API pull (2026-05-10 → 2026-05-11):**  
> Only 5 detections vs 56 from VIIRS. Confirms VIIRS is primary. MODIS confidence is numeric (0–100), not letters.

| Column | Type | Unit | Notes |
|--------|------|------|-------|
| `latitude`, `longitude` | float | ° | Same as VIIRS |
| `brightness` | float | K | Equivalent to VIIRS `bright_ti4` |
| `bright_t31` | float | K | Equivalent to VIIRS `bright_ti5` |
| `frp` | float | MW | Same definition. Values tend higher due to 1km pixel. |
| `confidence` | **int** | 0–100 | **Different from VIIRS — numeric!** Keep ≥50. |
| `satellite` | string | — | `Aqua` or `Terra` |
| `acq_date`, `acq_time` | same | — | Same format as VIIRS |

**Filter recipe:**
```python
# MODIS filter — confidence is a NUMBER not a letter
df_clean = df[(df['confidence'] >= 50) & (df['frp'] > 0)]
```

**VIIRS vs MODIS quick reference:**
```
VIIRS NOAA-20:  375m pixels, 2 passes/day, confidence = "n"/"h"/"l"  ← USE THIS
MODIS:          1km pixels,  4 passes/day, confidence = 0–100        ← cross-check only
```

---

## 2. Sentinel-5P TROPOMI — Chemical Smoke Signature

**What it does:** Satellite spectrometer that measures gas concentrations in the atmosphere. Used to confirm a pollution spike is from biomass burning (not city traffic or industry) by checking the chemical fingerprint.

**Access:** Google Earth Engine (GEE) — non-commercial project configured.  
**GEE Project ID:** `these-streets` (Google Cloud project #288828471914)  
**Google Cloud API Key:** `AIzaSyBFxTUEDoNdY6U3_AYKS6CYm2D72Asb9TE`  
**One-time setup:** Run `earthengine authenticate` in terminal, then `ee.Initialize(project='these-streets')`.  
**GEE Collection prefix:** `COPERNICUS/S5P/NRTI/L3_*`  
**Resolution:** ~3.5km × 5.5km  
**Latency:** ~3 hours after overpass

**Biomass burning "chemical fingerprint"** — all four should rise together:
```
NO2  > 2×10⁻⁵ mol/m²   → combustion
SO2  > 1×10⁻⁴ mol/m²   → burning / industrial
CO   > 0.03 mol/m²      → incomplete combustion — STRONGEST tracer
AAI  > 1.0              → absorbing aerosol (smoke or dust)

If all 4 elevated at same time/place = high confidence biomass burning plume.
```

**Quality filters (apply to all S5P bands):**
```python
# In GEE (JavaScript):
.filter(ee.Filter.lt('cloud_fraction', 0.3))  # discard cloudy pixels
.filter(ee.Filter.gt('qa_value', 0.75))       # discard bad retrievals
```

### Key bands by product

| Product | GEE collection | Band to use | Background | Fire plume |
|---------|---------------|------------|-----------|-----------|
| NO2 | `L3_NO2` | `tropospheric_NO2_column_number_density` | ~0.00002 mol/m² | >0.0001 mol/m² |
| SO2 | `L3_SO2` | `SO2_column_number_density` | ~0 mol/m² | >0.001 mol/m² |
| CO | `L3_CO` | `CO_column_number_density` | ~0.02 mol/m² | >0.05 mol/m² |
| AER_AI | `L3_AER_AI` | `absorbing_aerosol_index` | <0 (clean) | >1 (smoke), >3 (heavy) |

> **AER_AI note:** No `qa_value` for AER_AI. Instead filter: `solar_zenith_angle < 70`.

**GEE query template:**
```javascript
var s5p = ee.ImageCollection('COPERNICUS/S5P/NRTI/L3_NO2')
  .filterDate('2024-03-01', '2024-03-07')
  .filterBounds(ee.Geometry.Rectangle([102.0, 18.3, 109.7, 23.7]))
  .select('tropospheric_NO2_column_number_density')
  .filter(ee.Filter.lt('cloud_fraction', 0.3))
  .filter(ee.Filter.gt('qa_value', 0.75));
```

---

## 3. Open-Meteo — Wind & Meteorology

**What it does:** Provides hourly wind speed/direction at multiple altitudes + boundary layer height. Used to (a) verify where wind is pushing smoke and (b) estimate how concentrated the smoke will be when it arrives.

**No API key. Free. No rate limit.**  
**Base URL:** `https://api.open-meteo.com/v1/forecast`  
**Air Quality URL:** `https://air-quality-api.open-meteo.com/v1/air-quality`

> **Live data snapshot (Hanoi, 2026-05-12):**  
> - 850hPa wind: ~15–29 km/h, direction 178–251° (from south-southwest)  
> - BLH: 50–1320 m diurnal cycle (50m overnight = smoke trapped, 1300m afternoon = mixed up)  
> - PM2.5 forecast: 28–86 μg/m³ → US AQI 98–207 (already elevated, no fresh fire episode needed)  
> - AOD: 0.22–0.72 (significant aerosol loading)  
> - Total rain 3 days: 0.6 mm (almost none — smoke won't be washed out)

### Key wind variables

| Variable | Unit | Altitude | Why it matters |
|----------|------|---------|---------------|
| `wind_speed_850hPa` | km/h | ~1,500m | **Main smoke transport level for SE Asia. Use for travel-time estimate.** |
| `wind_direction_850hPa` | degrees | ~1,500m | **Direction smoke travels FROM.** 0=N, 90=E, 180=S, 270=W. |
| `wind_speed_700hPa` | km/h | ~3,000m | Upper transport — for lofted or convective smoke. |
| `wind_direction_700hPa` | degrees | ~3,000m | Upper transport direction. |
| `boundary_layer_height` | m | surface | **BLH: mixing depth.** Low at night → smoke concentrated. High afternoon → diluted. |
| `precipitation` | mm | surface | Rain scavenges particles → clears plume. |
| `cape` | J/kg | surface | Convective energy. High CAPE → smoke pushed higher → travels further. |

> **Wind direction convention:** Met direction = the direction wind is blowing **FROM**.  
> To get smoke travel direction: `smoke_goes_toward = (wind_direction + 180) % 360`

**Python — estimate smoke travel time:**
```python
import math, requests
from geopy.distance import geodesic

def wind_to_ms(speed_kmh, direction_deg):
    """Speed km/h + direction (from) → U, V components in m/s"""
    s = speed_kmh / 3.6
    rad = math.radians(direction_deg)
    return -s * math.sin(rad), -s * math.cos(rad)

def travel_time_hours(fire_lat, fire_lon, wind_speed_kmh):
    """Rough estimate: straight-line distance / wind speed"""
    dist_km = geodesic((fire_lat, fire_lon), (21.03, 105.85)).km
    return dist_km / wind_speed_kmh

# Example: fire at (20.5, 103.5), 850hPa wind = 20 km/h
print(f"~{travel_time_hours(20.5, 103.5, 20):.1f} hours")  # → ~14 hours
```

**Request pattern:**
```python
r = requests.get('https://api.open-meteo.com/v1/forecast', params={
    'latitude': 21.03,
    'longitude': 105.85,
    'hourly': 'wind_speed_850hPa,wind_direction_850hPa,boundary_layer_height,precipitation,cape',
    'pressure_level': '850,700',
    'forecast_days': 3,
    'timezone': 'Asia/Bangkok'
})
data = r.json()['hourly']  # dict of lists, one entry per hour
```

### Air Quality forecast variables

| Variable | Unit | Notes |
|----------|------|-------|
| `pm2_5` | μg/m³ | PM2.5 forecast. Smoke → this spikes first. |
| `aerosol_optical_depth` | 0–1 | Integrated aerosol column. Correlated with visibility. |
| `dust` | μg/m³ | Dust — helps separate smoke vs dust sources. |
| `us_aqi` | 0–500 | Pre-calculated US EPA AQI. |

---

## 4. HYSPLIT — Smoke Trajectory Model

**What it does:** Given a fire's GPS + timestamp + altitude, HYSPLIT simulates where the air parcel goes over time. "Forward trajectory" = trace smoke from fire toward Hanoi.

**Web interface (no install):** `https://www.ready.noaa.gov/HYSPLIT_traj.php`  
**Met data used:** GDAS 0.5° (global, 3-hourly) — auto-selected on web interface.

**Strategy — run 3 heights simultaneously:**
```
500m AGL  → smoke near ground (smoldering)
1000m AGL → typical transport height
1500m AGL → convective/lofted smoke

If ANY of the 3 arrives within 75km of Hanoi → flag as risk.
```

### HYSPLIT output file format (tdump)

The web interface gives you a `.txt` file. Parse it with `explore_hysplit.py` (`parse_tdump()` function).

**Key columns after parsing:**

| Column | Unit | Use |
|--------|------|-----|
| `traj_num` | — | Which of the 3 height trajectories (1, 2, 3) |
| `age_hr` | hours | Hours since fire start. **0 = fire location.** |
| `lat`, `lon` | ° decimal | Where the air parcel is at this time step |
| `height_m_agl` | m | How high above ground. Compare to BLH from Open-Meteo. |
| `dist_to_hanoi_km` | km | Added by `check_arrival()` function |

**Arrival detection (already coded in explore_hysplit.py):**
```python
from geopy.distance import geodesic

HANOI = (21.03, 105.85)
ARRIVAL_RADIUS_KM = 75

df['dist_to_hanoi_km'] = df.apply(
    lambda r: geodesic((r['lat'], r['lon']), HANOI).km, axis=1
)
arrivals = df[df['dist_to_hanoi_km'] <= ARRIVAL_RADIUS_KM]

if not arrivals.empty:
    first_age = arrivals['age_hr'].min()
    print(f"Smoke arrives in ~{first_age:.0f} hours")
```

> **Live synthetic test verified:** Parser correctly identified arrival at Hanoi in 9–12h for a fire at (20.5°N, 103.5°E) traveling at 850hPa wind speeds.

---

## 5. OpenAQ — Ground Truth Station Data

**What it does:** Real PM2.5 readings from physical monitors. Use to validate model predictions — if HYSPLIT says smoke arrives at 14:00, check if PM2.5 actually spiked at 14:00.

**Base URL:** `https://api.openaq.gov/v3/`  
**No auth for basic queries. Rate limited (be gentle).**

**Known Hanoi stations:**

| Station | Source | Note |
|---------|--------|------|
| US Embassy Hanoi | US DoS | Sometimes offline. Premium sensor. |
| Vietnam EPA network | VN gov | Multiple city stations. |

**Query PM2.5 for a specific station:**
```python
r = requests.get('https://api.openaq.gov/v3/locations', params={
    'city': 'Hanoi', 'country_id': 'VN', 'limit': 20
}, headers={'Accept': 'application/json'})

# Then pull measurements:
r2 = requests.get(f'https://api.openaq.gov/v3/locations/{station_id}/measurements',
    params={'parameter': 'pm25', 'limit': 168},  # 168 = 7 days hourly
    headers={'Accept': 'application/json'})
```

**Key response fields:**

| Field | Type | Notes |
|-------|------|-------|
| `value` | float | Measured concentration (μg/m³ or ppm — check `unit` field) |
| `period.datetimeTo.local` | ISO datetime | Hanoi local time (UTC+7) |
| `parameter.units` | string | Always check — CO sometimes in ppm |

---

## 6. WAQI — Current AQI & Forecast

**What it does:** Pre-calculated US EPA AQI values from stations worldwide. Easier to use than OpenAQ for current status and 3-day forecast.

**Token:** `cab9db60dd861a68c54b8fd73f2c17f7c5517f0a`

> **Live data snapshot (2026-05-12, Hanoi):**  
> - UN School station: **AQI 111 (Unhealthy for Sensitive Groups)**, PM2.5 = 111 μg/m³  
> - City station: AQI 60 (Moderate)  
> - US Embassy: offline  
> - PM2.5 forecast next 7 days: avg 109–182 (consistently elevated — likely regional fire season)

**Known Hanoi station UIDs:**

| UID | Name | Status |
|-----|------|--------|
| 8641 | Hanoi US Embassy (Đại sứ quán Mỹ) | Sometimes offline |
| 8688 | UN International School | Active, reliable |
| 1583 | Hanoi city aggregate | Active |
| 13026 | Hà Nội/Chi cục BVMT | Active |

**Query patterns:**
```python
TOKEN = 'cab9db60dd861a68c54b8fd73f2c17f7c5517f0a'

# Current AQI for Hanoi (nearest station)
r = requests.get(f'https://api.waqi.info/feed/hanoi/?token={TOKEN}')

# Specific station by UID
r = requests.get(f'https://api.waqi.info/feed/@8688/?token={TOKEN}')

# All stations in Hanoi bbox
r = requests.get(f'https://api.waqi.info/map/bounds/?latlng=20.8,105.5,21.3,106.2&token={TOKEN}')
```

**Key response fields:**

| Field | Unit | Notes |
|-------|------|-------|
| `data.aqi` | AQI | US EPA AQI. See scale below. |
| `data.iaqi.pm25.v` | μg/m³ | Raw PM2.5 (not AQI-converted) |
| `data.iaqi.pm10.v` | μg/m³ | Raw PM10 |
| `data.iaqi.t.v` | °C | Temperature at station |
| `data.iaqi.h.v` | % | Humidity |
| `data.iaqi.w.v` | m/s | Wind speed |
| `data.forecast.daily.pm25` | array | 3–8 day forecast: each item has `avg`, `max`, `min`, `day` |
| `data.time.s` | string | Local timestamp |

---

## 7. NASA POWER — Met at Fire Source Location

**What it does:** Gives you meteorological data (wind, humidity, rain, temp) **at the fire location itself** — not at Hanoi. Useful for understanding fire behavior and initial plume conditions.

**No API key. Free.**  
**Endpoint:** `https://power.larc.nasa.gov/api/temporal/hourly/point`

```python
r = requests.get('https://power.larc.nasa.gov/api/temporal/hourly/point', params={
    'parameters': 'WS10M,WD10M,RH2M,PRECTOTCORR,T2M',
    'community': 'RE',
    'longitude': fire_lon,
    'latitude': fire_lat,
    'start': '20240301',
    'end': '20240307',
    'format': 'JSON'
})
```

| Parameter | Unit | Meaning |
|-----------|------|---------|
| `WS10M` | m/s | Wind speed 10m at fire site |
| `WD10M` | ° | Wind direction at fire site |
| `RH2M` | % | Humidity — low = fire spreads faster |
| `PRECTOTCORR` | mm/hr | Rain — rain = fire weakens |
| `T2M` | °C | Temperature — hot + dry = intense fire |

---

## 8. CAMS — Global Smoke Forecast

**What it does:** Global atmospheric composition model that already tracks fire aerosol transport worldwide. Use as a baseline cross-check against your own HYSPLIT trajectory.

**Auth:** `cdsapi` with key in `~/.cdsapirc` (already configured).  
**One-time step:** Accept Terms of Use at `https://cds.climate.copernicus.eu/datasets/cams-global-atmospheric-composition-forecasts`

```python
import cdsapi

client = cdsapi.Client()
client.retrieve('cams-global-atmospheric-composition-forecasts', {
    'variable': ['particulate_matter_2.5um', 'organic_matter_aerosol_optical_depth_550nm'],
    'date': '2024-03-01/2024-03-07',
    'time': ['00:00', '06:00', '12:00', '18:00'],
    'leadtime_hour': ['0', '6', '12', '24', '48', '72'],
    'type': 'forecast',
    'data_format': 'netcdf',
    'area': [24, 102, 18, 110],  # north, west, south, east
}, 'cams_output.nc')
```

| Variable in output | Meaning |
|--------------------|---------|
| `pm2p5` | PM2.5 (μg/m³) |
| `aod550` | Aerosol Optical Depth at 550nm — measures smoke thickness |
| `bcaod550` | Black Carbon AOD — biomass burning specific |

---

## AQI Reference Scale (US EPA)

Used by WAQI. Use for explanation card severity labels.

| AQI | Level | PM2.5 (μg/m³) | Action |
|-----|-------|--------------|--------|
| 0–50 | **Good** / Tốt | 0–12 | No action needed |
| 51–100 | **Moderate** / Trung bình | 12.1–35.4 | Sensitive groups: be aware |
| 101–150 | **Unhealthy for Sensitive Groups** / Không tốt | 35.5–55.4 | Sensitive groups: limit outdoor time |
| 151–200 | **Unhealthy** / Có hại | 55.5–150.4 | Everyone: limit outdoor. Wear N95. |
| 201–300 | **Very Unhealthy** / Rất có hại | 150.5–250.4 | Avoid outdoor. Health alert. |
| 301–500 | **Hazardous** / Nguy hiểm | 250.5+ | Stay indoors. Close windows. |

> **Current baseline (2026-05-12):** Hanoi is already at AQI 111 (USG) without an identified fire episode. The explanation card should account for background pollution in its severity messaging.

---

## Bounding Boxes — Vùng Truy Vấn

| Region | West | South | East | North | Use |
|--------|------|-------|------|-------|-----|
| **Hanoi 300km** | **102.0** | **18.3** | **109.7** | **23.7** | **FIRMS query — use this** |
| Greater Mekong | 97.0 | 10.0 | 112.0 | 25.0 | Wider — catches Myanmar/Thai burning |
| Hanoi city | 105.5 | 20.8 | 106.2 | 21.3 | Ground station queries |

**Distance from fire to Hanoi:**
```python
from geopy.distance import geodesic

HANOI = (21.03, 105.85)

def km_to_hanoi(fire_lat, fire_lon):
    return geodesic((fire_lat, fire_lon), HANOI).km

# Reference distances:
# Northern Laos  (20.5°N, 103.0°E) → ~280km → ~14h at 20 km/h wind
# Myanmar border (21.0°N, 102.0°E) → ~360km → ~18h at 20 km/h wind
# Central Laos   (18.0°N, 103.5°E) → ~440km → ~22h at 20 km/h wind
```

---

## Pipeline Execution Order

```
Step 1  FIRMS VIIRS (NOAA-20 primary)
        ↳ Pull last 3 days, bbox 102.0,18.3,109.7,23.7
        ↳ Filter: confidence in [n,h] AND frp > 0
        ↳ Output: list of (lat, lon, frp, timestamp) fire events

Step 2  Open-Meteo at Hanoi
        ↳ Pull wind_speed_850hPa, wind_direction_850hPa, BLH
        ↳ Rough estimate: km_to_hanoi(fire) / wind_speed → hours

Step 3  HYSPLIT (for fires with frp > 50 MW, within ~600km)
        ↳ Forward trajectory from each significant fire
        ↳ 3 heights: 500m, 1000m, 1500m AGL
        ↳ Flag fires where any trajectory enters 75km radius of Hanoi

Step 4  Sentinel-5P (GEE) over smoke source area
        ↳ Check NO2 + SO2 + CO + AAI — confirms biomass burning signature
        ↳ Also check over Hanoi for arrival signal

Step 5  WAQI + OpenAQ
        ↳ Ground truth: did PM2.5 actually spike when HYSPLIT predicted?
        ↳ Stations: UID 8641 (US Embassy), UID 8688 (UN School)

Step 6  Assemble explanation card
        ↳ Source: fire at (lat, lon), frp=X MW, country=Y
        ↳ Transport: ~Z hours at 850hPa level
        ↳ Arrival: [datetime range]
        ↳ Severity: AQI prediction + current reading
        ↳ Duration: watch BLH + precipitation forecast for clearing signal
```
