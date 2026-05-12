# UI Improvement Plan

## Scope

This plan reviews the current Streamlit dashboard UI in `app/streamlit_app.py` and map rendering in `src/hanoi_air/viz.py`. The goal is to improve decision speed, readability, visual consistency, and production polish for an air-quality operations dashboard.

## Current UI Assessment

The dashboard already has a useful operational structure:

- Map-first workflow with district AQI, PM2.5 heatmap, regional cities, emission sources, and wind overlays.
- Sidebar controls for live/sample mode, refresh, forecast hour, and district selection.
- KPI row for max AQI, pollutant hotspots, alerts, and selected time.
- Detail panel with selected AQI, pollutants, wind, plume, health text, and top-5 worst districts.
- 24-hour chart with AQI uncertainty and PM2.5/NO2 trend lines.

The main improvement opportunity is not adding more widgets. It is making the existing information easier to scan, trust, and act on.

## Key Issues

### 1. Visual system is too concentrated in one dark-blue theme

The current palette is mostly dark navy with blue and purple accents. It works for a monitoring surface, but many components share the same contrast and visual weight. This makes the UI feel polished at first glance but less decisive under repeated use.

Recommended direction:

- Keep the dark operations-console base.
- Shift from decorative blue/purple emphasis to data-severity emphasis.
- Reserve strong colour for AQI severity, alerts, selected district, and active map layers.
- Use neutral slate/graphite for structure, not blue everywhere.

### 2. Information hierarchy needs a stronger decision path

The user should understand three things in under five seconds:

- Where is the worst air quality right now or at selected T+h?
- Why is it bad: background, traffic, plume, wind, or mixed?
- What action is recommended?

Current KPI cards are useful, but the main row treats system status, selected view, PM2.5, NO2, and alerts with similar emphasis.

Recommended direction:

- Make the selected/most severe district the primary object.
- Move data-source mode and generated time into a compact status strip.
- Give alerts a persistent high-priority position when present.
- Add a small "driver breakdown" block: background, traffic, plume, wind/ventilation.

### 3. Too much inline HTML/CSS makes refinement risky

`streamlit_app.py` currently mixes layout, styling, display helpers, and data selection. That slows iteration and increases the chance of inconsistent spacing, colours, and typography.

Recommended direction:

- Extract CSS into `app/assets/dashboard.css` or a Python string module such as `app/ui_theme.py`.
- Centralise component helpers in `app/ui_components.py`.
- Define shared tokens for colours, radii, spacing, type sizes, and AQI severity states.

### 4. Mobile and narrow viewport behaviour is not guaranteed

The dashboard uses fixed `st.columns(5)`, a 2.5/1 main layout, fixed map/chart heights, and compact metric text. This is fine on desktop, but the current structure may become cramped on small laptops or tablets.

Recommended direction:

- Reduce KPI row from five equal cards to a responsive summary: primary AQI card plus compact secondary metrics.
- Stack the detail panel below the map on narrow viewports.
- Use shorter labels and stable min heights for metric cards.
- Avoid long district names as card subtitles unless truncated or wrapped intentionally.

### 5. Map legend and overlays need clearer affordances

The map is rich, but users may not immediately know which layers are active or whether colours represent AQI, PM2.5 heatmap, or wind. The PM2.5 heatmap legend uses a separate scale from AQI severity, which is valid but needs clearer separation.

Recommended direction:

- Use a top-left map status chip: `T+Nh`, selected district, active pollutant.
- Split legends into "AQI district/station colour" and "PM2.5 heatmap intensity".
- Make selected district visually stronger and non-selected districts quieter.
- Add a "layers active" summary in the side panel, not only Leaflet LayerControl.

### 6. Accessibility and trust signals need improvement

The UI communicates severity mostly through colour. Some labels are small and low contrast. The user also needs confidence in data mode and uncertainty.

Recommended direction:

- Pair severity colours with labels and numeric thresholds.
- Increase minimum body/label contrast, especially `#475569` on dark backgrounds.
- Add visible uncertainty phrasing near the AQI number, not only in the chart.
- Show source freshness in human terms: "updated 12 min ago", "sample fallback", "Open-Meteo background".

### 7. Encoding/text rendering should be checked

The terminal output shows mojibake for Vietnamese and emoji text, even though the source likely intends UTF-8. This may be a console display issue, but it is worth verifying in the browser and exports.

Recommended direction:

- Confirm files are saved as UTF-8.
- Prefer fewer emoji in operational UI labels.
- Use text/icon semantics consistently instead of relying on emoji glyph rendering.

## Proposed Design Direction

Adopt an "Air Operations Console" direction:

- Dense but calm.
- Dark graphite base, AQI severity as the main colour language.
- Map as the primary visual workspace.
- Right panel as an incident-style readout.
- Less decorative glow, more measured contrast.
- Typography: functional, compact, consistent. If changing fonts, choose a Vietnamese-safe family with strong numeric rendering.

The interface should feel like a city operations room, not a marketing dashboard.

## Implementation Plan

### Phase 1: Quick Wins

Priority: High

- Replace repeated inline colour values with shared design tokens.
- Reduce purple/blue decorative gradients in buttons, slider, logo, and chart accents.
- Increase low-contrast text colours from muted slate to a more readable neutral.
- Make alert banner more actionable: show district count, worst district, max AQI, first exceedance time.
- Remove unused import `aqi_color` from `app/streamlit_app.py` if it remains unused.
- Add an empty/error state for `bundle["forecasts"]` before calling `max()`.

Acceptance criteria:

- Main dashboard still renders with `use_live=false`.
- KPI values remain identical to current logic.
- Text contrast improves without changing forecast outputs.

### Phase 2: Component Extraction

Priority: High

- Create `app/ui_theme.py` for tokens:
  - `AQI_COLORS`
  - `SURFACE_COLORS`
  - `TEXT_COLORS`
  - `RADIUS`
  - `SPACING`
- Create `app/ui_components.py` for:
  - `metric_card()`
  - `aqi_readout()`
  - `source_badge()`
  - `top5_row()`
  - `section_label()`
- Keep `streamlit_app.py` focused on data flow and layout.

Acceptance criteria:

- `streamlit_app.py` becomes easier to scan.
- No duplicated AQI colour mapping between component helpers.
- Visual output remains functionally equivalent after extraction.

### Phase 3: Layout Rework

Priority: High

- Convert top KPI row into a clearer hierarchy:
  - Primary: selected/worst AQI and district.
  - Secondary: PM2.5, NO2, alerts, T+h.
  - Status: data mode, generated time, source freshness.
- Reframe right panel as "District Readout":
  - AQI and category.
  - Recommendation.
  - Driver breakdown: background, plume, traffic, wind.
  - Uncertainty range.
  - Top-5 list.
- Keep map dominant, but reduce competing card borders around the surrounding UI.

Acceptance criteria:

- User can identify worst district, severity, and recommended action within one screen.
- Selected district detail is visibly connected to map selection.
- No card nesting or unnecessary decorative containers.

### Phase 4: Map UX

Priority: Medium

- Add a compact map header above the Folium iframe:
  - selected hour
  - selected district/all Hanoi
  - active layer summary
- Separate AQI legend from PM2.5 heatmap legend.
- Make selected district polygon and station marker more distinct.
- Review heatmap colour scale against AQI colours to reduce interpretation confusion.
- Add fallback copy when regional wind or city AQI layers are unavailable.

Acceptance criteria:

- Active map state is understandable without opening Leaflet LayerControl.
- Legends clearly state units and pollutant.
- Selected district is visible at a glance.

### Phase 5: Chart Improvements

Priority: Medium

- Use AQI severity bands with labelled threshold lines.
- Make uncertainty band visible but not visually dominant.
- Put selected district name in chart title area.
- Add a marker for the currently selected `T+h`.
- Consider a pollutant toggle for AQI, PM2.5, NO2 if Streamlit state remains simple.

Acceptance criteria:

- Chart explains forecast direction and risk range without needing table view.
- Hover labels are readable and consistent in Vietnamese.
- AQI and pollutant units are unambiguous.

### Phase 6: Accessibility And Responsiveness

Priority: Medium

- Define minimum font sizes:
  - 12px for metadata.
  - 14px for labels/body.
  - 18px+ for metrics.
- Ensure severity is not colour-only; include category labels.
- Check long Vietnamese district names in metric cards and top-5 rows.
- Test browser widths around 1440px, 1024px, and mobile-ish 390px.
- Add keyboard-friendly controls where Streamlit allows it.

Acceptance criteria:

- No text overlap at tested widths.
- Labels remain readable on dark background.
- UI remains usable when the sidebar is collapsed.

### Phase 7: Production Polish

Priority: Low

- Add a small source/freshness panel:
  - live API status
  - fallback status
  - cache age
  - source quality flags
- Add loading skeleton or compact loading message instead of blank spinner.
- Add visual regression screenshots if Playwright is introduced later.
- Consider a light print/export view for reports.

Acceptance criteria:

- Users can tell whether data is live, fallback, or cached.
- Dashboard feels stable during refresh.
- Export/report path does not depend on the dark interactive UI.

## Suggested File Changes

- `app/streamlit_app.py`: simplify data/layout orchestration.
- `app/ui_theme.py`: new shared design tokens.
- `app/ui_components.py`: new reusable Streamlit HTML helpers.
- `src/hanoi_air/viz.py`: refine map legends, layer labels, selected state, and colour scale comments.
- `tests/`: add lightweight tests for component formatting only if helpers include logic.

## Design Acceptance Checklist

- Worst district and AQI are obvious within five seconds.
- Alert state is visually and semantically distinct.
- Map legends do not mix AQI and PM2.5 concepts.
- No critical meaning depends on colour alone.
- Text remains readable on desktop and narrow widths.
- Data source mode and freshness are visible.
- Layout supports repeated operational use without decorative noise.

## Recommended First Sprint

1. Extract UI tokens and component helpers.
2. Rework KPI hierarchy and right-side district readout.
3. Improve alert banner and source freshness display.
4. Clean up map header/legend language.
5. Run `streamlit run app/streamlit_app.py` and inspect at desktop and narrow widths.

