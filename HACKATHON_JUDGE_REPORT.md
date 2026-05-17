# Hackathon Judge Report
## Asian Hackathon for Green Future 2026
**Project:** Hanoi Live Air Pollution Forecast (`vin-green-`)
**Challenge Area:** Urban Air Quality and Climate Resilience (Chủ đề 2)
**Evaluated against:** Competition Rules (Tiêu chí & Thể lệ) + Project Proposal Guideline
**Date of evaluation:** 2026-05-17

---

## Verdict

**Score: 66 / 100 — Borderline Top 30 candidate. Technically credible but fatally under-proven on impact, has a misleading AI claim, and presents a visualization rather than an intervention. Requires major sharpening before it can hold up against judge Q&A.**

---

## Compliance Check (Before Quality)

| Requirement | Status | Notes |
|---|---|---|
| Max 4 team members | ✅ Unknown — no member list in codebase | Must confirm in submission |
| Submission in English | ✅ All code, docs, README in English | Vietnamese appears only in district names |
| Proposal max 3 A4 pages / ~1,500 words | ⚠️ No proposal document found | Only technical codebase exists — **proposal must be written** |
| Selects exactly ONE challenge area | ✅ Urban Air Quality and Climate Resilience | Clear fit |
| Names team, project, members, challenge, category | ⚠️ Missing formal proposal structure | README exists but is not a competition proposal |
| Video introduction (~3 min) | ⚠️ No evidence of video | Must be produced |

**Critical compliance gap: The team has built a working system but has NOT yet produced the required proposal document or video. Both are mandatory for the preliminary round (deadline 17/5/2026 — today).**

---

## Project Thesis Identification

| Dimension | What the project claims / shows |
|---|---|
| **Problem** | Hanoi's air quality (PM2.5, NO₂, AQI) exceeds safe levels regularly. Real-time data is sparse (only 2–3 physical monitoring stations cover 12 inner districts). People have no reliable district-level pollution forecast to act on. |
| **Solution** | A hybrid forecasting system blending station observations (AQICN, OpenAQ), free global forecast background (Open-Meteo), Gaussian plume dispersion from industrial point sources, and a traffic congestion proxy — producing 24h district-level forecasts and downwind alerts. |
| **User** | Unclear. The system exposes a Streamlit dashboard and a FastAPI. There is no identified end-user segment, adoption pathway, or evidence of user demand. |
| **Mechanism** | Multi-source data fusion with IDW spatial interpolation → bias-corrected background blending → Gaussian plume addition → AQI computation. In theory: fuses sparse station data with modeled dispersion to produce spatially dense forecasts. |
| **Evidence** | Live API integrations verified (AQICN, OpenAQ v3, Open-Meteo). A live data snapshot (2026-05-12) shows AQI 111 at UN School Hanoi. No model accuracy metrics, no historical validation, no MAE/RMSE against ground truth. |
| **Demo** | Dockerized, runs in one command (`make up`). Streamlit dashboard + FastAPI endpoints. Can be shown live. The LSTM component exists in code but **is NOT connected to the forecast pipeline**. |

---

## Scorecard

| Category | Max | Score | Why |
|---|---:|---:|---|
| Problem specificity and urgency | 15 | 12 | Very specific geography (12 named Hanoi districts with GPS coordinates). Urgency is real — live AQI 111 observed. Deducted 3 because the baseline is poorly stated: no data on how many days/year Hanoi exceeds WHO PM2.5 guideline (15 µg/m³), no health burden cited, no comparison to regional averages. |
| Evidence, data, and stakeholder grounding | 10 | 5 | Real API integrations and a live data snapshot are positives. Fatal gap: zero model validation. Blend weights (0.55 obs + 0.45 background) are self-described as "tuned by eye, not learned." Uncertainty band is "purely heuristic, NOT a real prediction interval." No user research, no stakeholder interviews, no evidence that target users want this. |
| Existing solutions and gap analysis | 10 | 6 | IQAir, AQICN, AirVisual, and government SOMO/CEM systems all provide AQI data. The project's differentiation (multi-source fusion + Gaussian plume + district-level forecasting) is real but never articulated competitively. The claim that existing solutions "lack downwind alerts from industrial sources" is valid but unsubstantiated. |
| Solution clarity and core features | 15 | 11 | Architecture is exceptionally clear (FastAPI + Streamlit + Celery + Redis + Docker). Five distinct features demonstrable in the hackathon. Deducted 4 because: (1) LSTM is prominently scaffolded in the codebase but **completely disconnected from the forecast pipeline** — if presented as AI-powered, judges will discover this immediately; (2) the traffic proxy is a diurnal lookup table multiplied by road density, not actual traffic data. |
| Innovation and competitive advantage | 15 | 9 | Genuine innovations: multi-source priority cascade with circuit breakers, Gaussian plume approximation adding factory source contributions on top of background, and the `data_dictionary.md` satellite pipeline (FIRMS + Sentinel-5P + HYSPLIT) if real. Deducted 6 because: the satellite pipeline is documented but evidence of implementation in the main codebase is absent; the Gaussian plume is self-described as "not regulatory AERMOD"; the competitive advantage against IQAir's district-level forecasts is not demonstrated. |
| Technical architecture and implementation feasibility | 15 | 11 | Production-grade reliability is genuinely impressive for a student team: circuit breaker per source (3 failures → 5min cooldown), httpx + tenacity retries, atomic cache writes with filelock, Sentry-ready observability, multi-stage Docker build, 22 passing tests. AQI scale is US-EPA, not Vietnamese QCVN 06:2022/BTNMT — contextually wrong for a product targeting Vietnamese citizens. LSTM unused — if claimed in pitch, this is a kill-criteria violation. |
| Environmental, social, and economic impact | 10 | 4 | The proposal describes a visualization, not an intervention. No quantified impact: how many people are warned earlier? how many avoidable hospitalizations prevented? No pathway from "dashboard exists" to "pollution decreases" or "health outcomes improve." Impact section in proposal guideline (Section 6) cannot be answered by this codebase alone. |
| Hackathon execution plan, roadmap, and communication | 10 | 8 | `make up` gives a full running demo — this is the team's strongest asset in the 24h hackathon. Roadmap exists in CLAUDE.md (Phases 0–6). Deducted 2 because the roadmap is internal development documentation, not a competition-facing impact timeline, and CI/CD is missing. |
| **TOTAL** | **100** | **66** | |

---

## Fatal Weaknesses

### 1. The LSTM claim is hollow — this will cost the team heavily

The codebase explicitly states: *"The `LSTMForecaster` class in model.py exists but is **not called** by the forecast pipeline. It's training scaffolding only."* The forecast pipeline at `src/hanoi_air/forecast.py` uses a purely heuristic formula:

```
pm25_final = blend(0.55·obs + 0.45·bg) × diurnal × seasonal × ventilation + traffic_index + plume_contribution
```

If the team presents this as an "AI-powered" or "machine learning" forecast, judges will ask: "Show us your model training loss curve." "What's your RMSE vs. a naive persistence baseline?" There are no answers. This does not mean the solution is weak — it means the team must accurately describe what they have built, not what they intended to build.

### 2. Zero model validation — the forecast is unverified

The blend weights are the team's own words: *"tuned by eye, not learned."* The confidence bands are *"purely heuristic, NOT a real prediction interval."* The system produces numbers that look precise (e.g., "PM2.5: 47.3 µg/m³") but there is no demonstrated correlation between the model output and actual ground truth measurements. Judges in a science-grounded hackathon will ask for a holdout comparison. The team has none.

### 3. Visualization vs. intervention — no adoption mechanism

The project produces a dashboard and an API. Who sees the dashboard? How does seeing it change behavior? What is the pathway from "this API exists" to "less pollution exposure"? Without an answer, the project scores 4/10 on impact — which is a killer, since impact is a core judging criterion. A weather app that nobody downloads protects nobody.

### 4. AQI scale is wrong for the context

The system uses US-EPA AQI breakpoints. Vietnam has a national standard: **VN_AQI per QCVN 06:2022/BTNMT**. The CLAUDE.md explicitly flags this as a gap. A system intended for Vietnamese citizens, evaluated by judges from Vietnamese institutions (Vingroup, VinUni), using the wrong national air quality standard is a credibility problem. The US AQI "Good" band (0–50) does not map to the same health guidance as the Vietnamese equivalent.

### 5. Data sparsity undermines the spatial claim

The system claims district-level forecasts for 12 districts. AQICN's geo query returns the nearest physical station — the codebase confirms: *"querying 12 district centroids may return only 2–3 unique stations."* IDW interpolation with 2–3 input points across 12 districts is not district-level precision — it is spatial extrapolation with very high uncertainty. This should be disclosed, not hidden.

### 6. The satellite pipeline (FIRMS + HYSPLIT) is documented but not demonstrated

`data_dictionary.md` describes an impressive upstream pipeline: FIRMS fire detection → Sentinel-5P chemical fingerprinting → HYSPLIT trajectory modeling → Hanoi arrival alert. API keys are configured, live data snippets are shown. But this pipeline is not present in `src/hanoi_air/` — it appears to be a research notebook / documentation artifact. If this capability were actually implemented and demoable, the innovation score would jump to 13+/15. Right now it counts for nothing because it cannot be shown.

---

## What Would Impress Judges

1. **Connect the LSTM or delete it.** Train on 30 days of archived Open-Meteo + AQICN data from `data/processed/`. Show a loss curve, a validation MAE, and a comparison against the current heuristic baseline on a holdout week. Even a mediocre trained model with honest validation beats an impressive heuristic with no validation.

2. **Run one HYSPLIT trajectory live.** The FIRMS data is pulling real fires within 600km of Hanoi. Run one forward trajectory for the highest-FRP fire visible right now, show it arriving or not arriving at Hanoi, and display it on the Folium map. This single feature — "satellite detects fire → 14 hours before it reaches Hanoi, the system warns you" — is the most compelling and differentiated story in the entire project. It changes the project from a dashboard to an early-warning system.

3. **Add one quantified impact claim.** Use WHO guidelines: Hanoi exceeds WHO PM2.5 annual mean (15 µg/m³) on approximately [X]% of days (this can be computed from the archived data). If 24h advance warning allowed [Y]% of sensitive-group residents to stay indoors on high-pollution days, that represents [Z] avoided hospital admissions per year at [V] VND cost per admission. Even rough numbers with honest caveats are vastly better than no numbers.

4. **Switch to VN_AQI.** Implement Vietnamese national standard (QCVN 06:2022/BTNMT). This is a flag in `air_quality.py`. It signals that the team understands their deployment context.

5. **Name and interview one user.** "We spoke with 5 residents of Bắc Từ Liêm, which our model identifies as the highest-AQI district, and 4 of 5 said they would change outdoor activity plans if warned 4 hours in advance" — this single sentence answers the adoption mechanism question that currently has no answer.

6. **Show the source health panel.** The system tracks which data sources are live vs. degraded vs. circuit-broken. A real-time source status UI demonstrates production thinking. Expose `GET /sources` and add a panel to the dashboard. This is a 2-hour addition that demonstrates operational maturity.

---

## Questions Judges Will Ask

1. "Your model uses coefficients like 0.55, 0.46, and 0.18. Where do these come from? What happens if they're wrong by 30%?"

2. "You mention AERMOD-style Gaussian plume. Have you compared your plume estimates against actual downwind station readings? What's the error?"

3. "IQAir and AQICN already show AQI by district in Hanoi. What does your forecast tell a user that they cannot get from those free services?"

4. "You have an LSTM class in your code. Is it trained? What data did you use? What's the prediction error compared to your current heuristic model?"

5. "Who uses this dashboard today? Can you show a user or stakeholder who changed a behavior because of your system?"

6. "Hanoi has approximately 8.5 million residents. How does your forecast reach them? What's your go-to-market plan beyond a Streamlit app running on localhost?"

7. "Your system uses US-EPA AQI. Vietnamese QCVN 06:2022/BTNMT has different breakpoints. Why did you choose the US standard for a Vietnamese product?"

8. "If your main data source (AQICN) goes down, how does your forecast degrade? Is the degradation communicated to users?"

9. "You mention FIRMS satellite fire data and HYSPLIT trajectories in your documentation. Is that pipeline running live? Can you show it?"

10. "Your uncertainty band grows with forecast horizon. Why should a user trust your hour-22 forecast? What's the uncertainty at hour-22 vs. hour-1?"

---

## Rescue Plan (Priority Order for the Next 48–72 Hours)

### Step 1 — Fix the thesis (TODAY, 2 hours)

Reframe the project from "AQI dashboard" to **"upstream smoke early-warning system."** The thesis is: *Hanoi residents currently have no warning before a smoke episode from regional biomass burning arrives. We detect fires via satellite, trace their path via trajectory modeling, and deliver a district-level arrival alert 12–24 hours in advance.* This is defensible, specific, and novel. The heuristic forecast becomes the background model. The FIRMS+HYSPLIT pipeline becomes the headline feature.

### Step 2 — Demonstrate the satellite pipeline (TODAY/TOMORROW, 6–8 hours)

Take the `data_dictionary.md` code and make it runnable end-to-end in a notebook:
1. Pull FIRMS VIIRS NOAA-20 for the last 3 days (code exists in `data_dictionary.md`)
2. Filter fires with `confidence in ['n','h']` and `frp > 50 MW` within 600km of Hanoi
3. Run HYSPLIT web form (no install required) for the top-FRP fire
4. If any trajectory enters 75km of Hanoi, fire an alert
5. Show this on the Folium map as a distinct layer ("Incoming smoke from [country], arrives ~[time]")

This is the prototype that can be shown in 24 hours at VinUni. It changes the judging conversation entirely.

### Step 3 — Add one validation number (TOMORROW, 3 hours)

Run the heuristic forecast against 7 days of archived AQICN readings already in `data/processed/`. Compute MAE and compare to a persistence baseline (tomorrow = today). Even if the model wins by only 15%, that's a result. Even if it loses, honesty about the gap is better than no number at all.

### Step 4 — Switch to VN_AQI (TOMORROW, 2 hours)

Implement `src/hanoi_air/air_quality.py` to support Vietnamese QCVN 06:2022/BTNMT breakpoints alongside the current US-EPA implementation. Add a `use_vn_aqi: bool` flag in Settings. Default to VN_AQI in the UI. This is a mechanical implementation — the breakpoints are publicly available.

### Step 5 — Quantify impact and write the proposal (TOMORROW, 3 hours)

Compute from archived data:
- Median PM2.5 per district across the last 30 days
- Number of days exceeding WHO 24h guideline (15 µg/m³) and VN QCVN standard
- Correlation between wind direction and PM2.5 spikes (evidence that the plume model captures something real)

Use these numbers in the proposal. Write the proposal following the 7-section guideline. Max 3 A4 pages. Submit before deadline.

### Step 6 — Trim the pitch narrative (HACKATHON DAY, 1 hour)

Drop or honest-label the LSTM. Say explicitly: *"We have built an LSTM training scaffold. In the hackathon, we replaced it with a physics-informed heuristic to meet the 24h deadline. The LSTM is the next planned upgrade once we have 90 days of validated training data."* This is honest and shows forward planning — judges respect this more than a hollow AI claim.

---

## Grade Band Assessment

| Scenario | Score | Band |
|---|---:|---|
| **Current state** (as-is, with honest framing) | 66 | Plausible but vulnerable — unlikely without major revision |
| **After Steps 1–3** (thesis reframe + satellite demo + validation number) | 78–82 | Strong Top 30 candidate |
| **After all 6 steps** (complete rescue) | 83–88 | Finalist-quality — hard to dismiss |

The gap between 66 and 83 is not technical — the code is already good. The gap is in framing, validation, and the one feature (satellite→trajectory→alert) that transforms this from a monitoring dashboard into a predictive intervention system.

---

## Technical Strengths (What to Protect)

These are genuine strengths that should be highlighted in the pitch, not buried:

- **Production-grade reliability**: Circuit breaker, exponential backoff retries, atomic cache writes, Sentry — this is engineering discipline rarely seen in student hackathon projects.
- **Multi-source priority cascade**: The system degrades gracefully when live sources fail, falling through AQICN → OpenAQ → crawlers → sample data. This is a real resilience design.
- **Dockerized full-stack demo**: `make up` brings up 4 services in under 2 minutes. The demo works.
- **Data archive foundation**: Raw payloads archived under `data/raw/{source}/YYYY-MM-DD/` means the team is building toward historical validation — they just haven't run it yet.
- **Gaussian plume is real physics**: Unlike most hackathon "AI" solutions that are pattern-matching on dashboards, the team has implemented a physically-grounded dispersion model for factory sources. This is a genuine differentiator.
- **Live data confirmed**: The WAQI snapshot (AQI 111 at UN School, 2026-05-12) and FIRMS fire detections (56 VIIRS events in 3 days) show the pipelines actually pull real data — this is not a demo with hardcoded values.

---

*Report generated per SKILL.md judging protocol. Evaluation is based entirely on code, documentation, and data files present in the repository as of 2026-05-17. No oral pitch or video was evaluated. Score may differ from final competition result based on presentation quality and judge discretion.*
