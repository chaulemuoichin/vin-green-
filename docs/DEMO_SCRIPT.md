# 30-Second Pitch Demo Script

A walkthrough for live pitch. Total runtime ~30 seconds plus a 30-second curl chaser.

## Setup (one-time, before the pitch)

```powershell
cp .env.example .env
# Set API_KEYS=demo,pitch in .env (the dashboard does not need a key — only the API)
make prod-build
make prod-up
# Wait ~30 s for healthchecks; open http://localhost/ in a tab pre-warmed.
```

## Stage layout

- **Browser tab A** (foreground): http://localhost/ — the Streamlit dashboard
- **Browser tab B** (preloaded): http://localhost/docs — OpenAPI swagger
- **Terminal** (preloaded with the curl commands below, not yet executed)

## The 30-second narration

> **(0:00–0:05) Open on the dashboard map.**
> "This is 24-hour AQI for 15 Hanoi districts. The dark patches on the map are the worst — Bắc Từ Liêm and Sơn Tây today."

> **(0:05–0:10) Drag the hour slider to T+8 (08:00 local).**
> "At the morning rush, Hoàn Kiếm hits AQI 162. The wedge shows it's downwind of the Minh Khai industrial cluster under the south-southeast wind."

> **(0:10–0:15) Click the "🥧 Nguồn ô nhiễm" tab.**
> "We don't just say 'it's bad' — we say why. 56 % traffic, 17 % industry, 12 % agricultural burning. Each slice is computed from live signals, not just an inventory chart."

> **(0:15–0:20) Click the "✅ Hành động" tab.**
> "For citizens: N95 between 8 and 10, take the bus instead of the bike. For the city: truck restriction on Phạm Văn Đồng 6–10 and 16–20, inspect the Minh Khai stack while the wind aligns."

> **(0:20–0:25) Click the "🇻🇳 VN_AQI" tab.**
> "Both scales side-by-side — the regulatory Vietnamese QCVN reading and the US-EPA one international audiences recognise. Auditors can verify either way."

> **(0:25–0:30) Click the "📐 Độ chính xác" tab.**
> "We're not asking you to trust us — we backtest every hour against OpenAQ. Today's RMSE on PM2.5 is *[value from latest snapshot]* µg/m³, beating a persistence baseline by *[delta]*."

## The 30-second curl chaser

```powershell
# Switch to the terminal. These take ~3 seconds combined.
curl -H "X-API-Key: demo" "http://localhost/api/forecast?district=hoan_kiem&hours=1&fields=vn_aqi,actions,source_breakdown,downwind_risk" | jq
```

> "And this all comes out of a single API call — district scoped, field allow-listed, JWT-style auth, slowapi rate limiting. A mobile client only pulls the bytes it needs. Production-ready, today."

## Common Q&A

- **"Where does the data come from?"** OpenAQ + AQICN for stations, Open-Meteo for wind and CAMS-style background (free, no key), Overpass for road density, NASA FIRMS for fire detections. Every source has cadence + freshness gating + a circuit breaker, so a dead endpoint never wedges the dashboard.
- **"What if the LSTM is wrong?"** It only blends in when its 7-day RMSE beats the heuristic, and even then it's weighted 30 % vs 70 % heuristic. Worst case is the heuristic alone — the floor never drops.
- **"Why these 15 districts?"** 12 canonical inner urban districts plus Hoài Đức, Thạch Thất, and Sơn Tây — the peri-urban corridor where the cement and brick clusters sit. Adding the others is a CSV append plus a receptor entry; the rest of the pipeline is district-agnostic.
- **"Can we run it offline?"** Yes — `use_live=false` falls back to sample CSVs and Open-Meteo's free endpoint. The dashboard never throws on a missing key.
- **"Show me a curl that fails."** `curl http://localhost/api/forecast` without an API key returns `401 — Missing API key. Provide X-API-Key header.` Then `curl -H "X-API-Key: wrong" ...` returns `401 Invalid API key.` Both are visible in the response headers within OpenAPI.

## Reset between takes

```powershell
make prod-down
docker volume rm hanoi_air_redis_data_prod hanoi_air_cache_data_prod  # optional cache wipe
make prod-up
```
