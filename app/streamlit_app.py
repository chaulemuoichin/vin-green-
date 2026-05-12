from __future__ import annotations

import sys
from datetime import datetime, timezone
from pathlib import Path
from textwrap import dedent

ROOT = Path(__file__).resolve().parents[1]
APP_DIR = Path(__file__).resolve().parent
sys.path.insert(0, str(ROOT / "src"))
sys.path.insert(0, str(APP_DIR))

import streamlit as st

from hanoi_air.config import get_settings
from hanoi_air.forecast import build_cached_forecast, top_n_worst
from hanoi_air.geography import load_districts
from hanoi_air.observability import init_sentry
from hanoi_air.viz import build_folium_map
from ui_components import (
    alert_banner,
    aqi_legend,
    driver_breakdown,
    map_header,
    metric_card,
    primary_aqi_summary,
    recommendation_card,
    section_label,
    status_strip,
    top5_row,
)
from ui_theme import ACCENTS, TEXT_COLORS, aqi_state, global_css

init_sentry(service="dashboard")

st.set_page_config(
    page_title="Northern Vietnam Air Forecast",
    page_icon="AQ",
    layout="wide",
    initial_sidebar_state="expanded",
)

st.markdown(global_css(), unsafe_allow_html=True)


def _html(value: str) -> str:
    return " ".join(line.strip() for line in dedent(value).strip().splitlines())


@st.cache_data(ttl=1800, show_spinner=False)
def _load_bundle(use_live: bool, force: bool) -> dict:
    return build_cached_forecast(get_settings(), force_refresh=force, use_live=use_live)


def _freshness_note(bundle: dict) -> str:
    status = bundle.get("source_status") or {}
    successes = [
        item
        for item in status.values()
        if isinstance(item, dict) and item.get("ok") and item.get("last_success_at")
    ]
    if not successes:
        return "No live freshness record"
    latest = max(str(item["last_success_at"]) for item in successes)
    try:
        parsed = datetime.fromisoformat(latest)
        if parsed.tzinfo is None:
            parsed = parsed.replace(tzinfo=timezone.utc)
        minutes = max(0, round((datetime.now(timezone.utc) - parsed.astimezone(timezone.utc)).total_seconds() / 60))
        return f"freshest source {minutes} min ago"
    except ValueError:
        return f"freshest source {latest[:16].replace('T', ' ')}"


def _select_main_row(rows: list[dict], selected_district: str | None) -> dict | None:
    if not rows:
        return None
    selected_rows = [
        row for row in rows if selected_district is None or row["district_id"] == selected_district
    ]
    return max(selected_rows or rows, key=lambda row: int(row["aqi"]))


def _chart(bundle: dict, selected_district: str | None, selected_label: str, main_row: dict, hour: int) -> None:
    try:
        import pandas as pd
        import plotly.graph_objects as go
    except Exception as exc:
        st.warning(f"Chart dependencies unavailable: {exc}")
        return

    if selected_district:
        series = [r for r in bundle["forecasts"] if r["district_id"] == selected_district]
        title_str = selected_label
    else:
        series = [r for r in bundle["forecasts"] if r["district_id"] == main_row["district_id"]]
        title_str = f"{main_row['district_name']} - current hotspot"
    if not series:
        st.info("No forecast series available for the selected district.")
        return

    df_chart = pd.DataFrame(series).sort_values("hour_offset")
    fig = go.Figure()

    for y0, y1, label in [
        (0, 50, "Tot"),
        (50, 100, "Trung binh"),
        (100, 150, "Khong tot"),
        (150, 200, "Xau"),
        (200, 300, "Rat xau"),
    ]:
        color = str(aqi_state(y1)["color"])
        fig.add_hrect(y0=y0, y1=y1, fillcolor=color, opacity=0.045, line_width=0)
        fig.add_hline(y=y1, line_color="rgba(255,255,255,0.08)", line_width=1)
        if y1 in {100, 150, 200}:
            fig.add_annotation(
                x=23,
                y=y1,
                text=label,
                showarrow=False,
                font=dict(size=10, color="#8794a3"),
                xanchor="right",
                yshift=8,
            )

    fig.add_trace(
        go.Scatter(
            x=list(df_chart["hour_offset"]) + list(df_chart["hour_offset"])[::-1],
            y=list(df_chart["uncertainty_high"]) + list(df_chart["uncertainty_low"])[::-1],
            fill="toself",
            fillcolor="rgba(158,197,255,0.095)",
            line=dict(width=0),
            name="Uncertainty",
            hoverinfo="skip",
        )
    )
    fig.add_trace(
        go.Scatter(
            x=df_chart["hour_offset"],
            y=df_chart["aqi"],
            name="AQI",
            mode="lines+markers",
            line=dict(color=str(aqi_state(int(main_row["aqi"]))["color"]), width=2.8),
            marker=dict(size=5),
            hovertemplate="T+%{x}h | AQI <b>%{y}</b><extra></extra>",
        )
    )
    fig.add_trace(
        go.Scatter(
            x=df_chart["hour_offset"],
            y=df_chart["pm25"],
            name="PM2.5 ug/m3",
            mode="lines",
            line=dict(color=ACCENTS["pm25"], width=1.9, dash="dot"),
            yaxis="y2",
            hovertemplate="PM2.5 <b>%{y:.1f}</b> ug/m3<extra></extra>",
        )
    )
    fig.add_trace(
        go.Scatter(
            x=df_chart["hour_offset"],
            y=df_chart["no2"],
            name="NO2 ug/m3",
            mode="lines",
            line=dict(color=ACCENTS["no2"], width=1.9, dash="dot"),
            yaxis="y2",
            hovertemplate="NO2 <b>%{y:.1f}</b> ug/m3<extra></extra>",
        )
    )

    fig.add_vline(x=hour, line_color="rgba(238,242,246,0.42)", line_dash="dash", line_width=1)
    fig.add_annotation(
        x=hour,
        y=max(10, int(main_row["aqi"])),
        text=f"T+{hour}h",
        showarrow=True,
        arrowhead=2,
        arrowcolor="rgba(238,242,246,0.55)",
        font=dict(size=11, color="#eef2f6"),
        bgcolor="rgba(7,9,7,0.75)",
        bordercolor="rgba(230,238,232,0.16)",
    )

    fig.update_layout(
        title=dict(text=title_str, font=dict(size=14, color=TEXT_COLORS["primary"])),
        paper_bgcolor="rgba(0,0,0,0)",
        plot_bgcolor="rgba(255,255,255,0.022)",
        font=dict(color=TEXT_COLORS["secondary"], family="IBM Plex Sans", size=11),
        height=300,
        margin=dict(l=0, r=0, t=36, b=0),
        hovermode="x unified",
        legend=dict(
            bgcolor="rgba(18,22,20,0.86)",
            bordercolor="rgba(230,238,232,0.105)",
            borderwidth=1,
            font=dict(size=11),
            x=0.01,
            y=0.98,
        ),
        xaxis=dict(
            title="Forecast hour (T+h)",
            gridcolor="rgba(255,255,255,0.055)",
            zeroline=False,
            tickfont=dict(color=TEXT_COLORS["muted"]),
            title_font=dict(color=TEXT_COLORS["muted"], size=10),
        ),
        yaxis=dict(
            title="AQI",
            gridcolor="rgba(255,255,255,0.055)",
            zeroline=False,
            tickfont=dict(color=TEXT_COLORS["muted"]),
            title_font=dict(color=TEXT_COLORS["muted"], size=10),
        ),
        yaxis2=dict(
            title="ug/m3",
            overlaying="y",
            side="right",
            gridcolor="rgba(0,0,0,0)",
            zeroline=False,
            tickfont=dict(color=TEXT_COLORS["muted"]),
            title_font=dict(color=TEXT_COLORS["muted"], size=10),
        ),
    )
    st.plotly_chart(fig, use_container_width=True, config={"displayModeBar": False})


districts = load_districts()
district_options = {"Toan Ha Noi": None}
district_options.update({district.name: district.district_id for district in districts})

with st.sidebar:
    st.markdown(
        """
        <div style="display:flex;align-items:center;gap:10px;margin-bottom:2px">
            <div style="width:32px;height:32px;background:#62d6b1;border-radius:7px;
                display:flex;align-items:center;justify-content:center;color:#07100c;
                font-weight:800;font-family:'IBM Plex Mono',monospace">AQ</div>
            <div>
                <div style="color:#eef2f6;font-size:1.04rem;font-weight:700">Hanoi Air</div>
                <div style="color:#8794a3;font-size:.72rem">Operations console</div>
            </div>
        </div>
        """,
        unsafe_allow_html=True,
    )
    st.divider()
    use_live = st.toggle("Live data", value=True)
    force_refresh = st.button("Refresh now", use_container_width=True)
    st.divider()
    hour = st.slider("Forecast hour", 0, 23, 0, format="T+%dh")
    selected_label = st.selectbox("District", list(district_options.keys()))
    selected_district = district_options[selected_label]
    st.divider()
    st.markdown(
        '<div style="color:#8794a3;font-size:.76rem;line-height:1.6">'
        '<b style="color:#b6c2cf">Tracked sources</b><br>'
        'AQICN / OpenAQ / Open-Meteo / public crawlers'
        '</div>',
        unsafe_allow_html=True,
    )

with st.spinner("Loading forecast bundle..."):
    bundle = _load_bundle(use_live, force_refresh)

forecasts = bundle.get("forecasts") or []
if not forecasts:
    st.error("No forecast rows were returned. Check data sources or sample files.")
    st.stop()

hour_rows = [row for row in forecasts if int(row["hour_offset"]) == hour]
if not hour_rows:
    hour_rows = forecasts[: len(districts)]

main_row = _select_main_row(hour_rows, selected_district)
if main_row is None:
    st.error("No forecast rows are available for the selected view.")
    st.stop()

aqi_val = int(main_row["aqi"])
aqi_colour = str(aqi_state(aqi_val)["color"])
source_note = _freshness_note(bundle)

title_col, status_col = st.columns([1.55, 1])
with title_col:
    st.markdown(
        '<h1 class="air-title">Northern Vietnam Air Quality Forecast</h1>'
        '<div class="air-subtitle">Hanoi districts, regional context, wind and PM2.5 transport risk</div>',
        unsafe_allow_html=True,
    )
with status_col:
    st.markdown(
        status_strip(
            str(bundle.get("generated_at") or ""),
            str(bundle.get("mode") or "unknown"),
            len(bundle.get("source_registry") or bundle.get("sources") or []),
            source_note,
        ),
        unsafe_allow_html=True,
    )

st.markdown("<div style='margin-bottom:10px'></div>", unsafe_allow_html=True)
st.markdown(alert_banner(bundle.get("alerts") or [], main_row), unsafe_allow_html=True)

_fire_alerts = bundle.get("fire_alerts") or []
_fire_stats = bundle.get("fire_filter_stats") or {}
if _fire_alerts:
    st.warning(
        f"**Cháy rừng upwind**: {len(_fire_alerts)} điểm cháy có rủi ro cao, "
        f"khói dự kiến ảnh hưởng Hà Nội trong 24h tới."
    )
    for _fa in _fire_alerts[:3]:
        st.markdown(f"- {_fa['message']}")
    if _fire_stats.get("total_fires", 0) > 0:
        with st.expander("Thống kê lọc fire (hex grid)"):
            _fc1, _fc2, _fc3 = st.columns(3)
            _fc1.metric("Tổng fires", _fire_stats.get("total_fires", 0))
            _fc2.metric("High risk", _fire_stats.get("high_risk_count", 0))
            _fc3.metric(
                "Đã lọc bỏ",
                _fire_stats.get("low_risk_count", 0),
                delta=f"-{_fire_stats.get('compute_saved_minutes', 0):.0f} min HYSPLIT",
            )

summary_col, metric_col = st.columns([1.65, 2.15])
with summary_col:
    st.markdown(primary_aqi_summary(main_row, selected_label), unsafe_allow_html=True)
with metric_col:
    m1, m2, m3, m4 = st.columns(4)
    m1.markdown(metric_card("Max AQI", str(bundle.get("max_aqi", aqi_val)), "bundle", aqi_colour), unsafe_allow_html=True)
    m2.markdown(metric_card("Alerts", str(len(bundle.get("alerts") or [])), "districts", ACCENTS["danger"] if bundle.get("alerts") else "#2fdd8a"), unsafe_allow_html=True)
    m3.markdown(metric_card("Viewing", f"T+{hour}h", selected_label, ACCENTS["wind"]), unsafe_allow_html=True)
    m4.markdown(metric_card("Mode", str(bundle.get("mode") or "unknown").replace("_", " ").title(), "data", TEXT_COLORS["secondary"]), unsafe_allow_html=True)

st.markdown("<div style='margin-bottom:10px'></div>", unsafe_allow_html=True)

map_col, readout_col = st.columns([2.45, 1.0])

with map_col:
    tab_map, tab_table = st.tabs(["Map", "Data table"])
    with tab_map:
        st.markdown(
            map_header(
                hour,
                selected_label,
                bool(bundle.get("wind_grid")),
                bool(bundle.get("regional_cities")),
            ),
            unsafe_allow_html=True,
        )
        map_obj = build_folium_map(bundle, hour_offset=hour, selected_district=selected_district)
        if map_obj is None:
            st.error("Install map dependencies: `pip install folium streamlit-folium`")
        else:
            try:
                from streamlit_folium import st_folium  # type: ignore

                st_folium(
                    map_obj,
                    width=None,
                    height=590,
                    returned_objects=[],
                    key=f"map_ops_v3_{hour}_{selected_district}",
                )
            except Exception:
                st.components.v1.html(map_obj._repr_html_(), height=590)
        st.markdown(aqi_legend(), unsafe_allow_html=True)

    with tab_table:
        try:
            import pandas as pd

            df = (
                pd.DataFrame(hour_rows)[
                    [
                        "district_name",
                        "aqi",
                        "pm25",
                        "no2",
                        "category",
                        "wind_speed_mps",
                        "uncertainty_low",
                        "uncertainty_high",
                    ]
                ]
                .sort_values("aqi", ascending=False)
                .rename(
                    columns={
                        "district_name": "District",
                        "aqi": "AQI",
                        "pm25": "PM2.5 ug/m3",
                        "no2": "NO2 ug/m3",
                        "category": "Severity",
                        "wind_speed_mps": "Wind m/s",
                        "uncertainty_low": "AQI min",
                        "uncertainty_high": "AQI max",
                    }
                )
            )
            st.dataframe(df, use_container_width=True, hide_index=True, height=560)
        except Exception:
            st.json(hour_rows[:12])

with readout_col:
    district_label = selected_label if selected_label != "Toan Ha Noi" else str(main_row["district_name"])
    st.markdown(section_label("District readout"), unsafe_allow_html=True)
    st.markdown(
        _html(f"""
        <div style="border:1px solid {aqi_colour}55;background:{aqi_colour}12;border-radius:8px;
            padding:14px 15px;margin-bottom:9px">
            <div style="color:{TEXT_COLORS['secondary']};font-size:.75rem;text-transform:uppercase;
                letter-spacing:.07em;font-weight:700">{district_label}</div>
            <div style="display:flex;align-items:baseline;gap:10px;margin-top:5px">
                <span style="font-family:'IBM Plex Mono',monospace;font-size:3rem;font-weight:700;
                    color:{aqi_colour};line-height:1">{aqi_val}</span>
                <span style="color:{aqi_colour};font-size:.95rem;font-weight:700">{aqi_state(aqi_val)['label']}</span>
            </div>
            <div style="color:{TEXT_COLORS['secondary']};font-size:.82rem;margin-top:8px">
                Uncertainty range {main_row['uncertainty_low']}-{main_row['uncertainty_high']} AQI
            </div>
        </div>
        """),
        unsafe_allow_html=True,
    )
    p1, p2 = st.columns(2)
    p1.markdown(metric_card("PM2.5", str(main_row["pm25"]), "ug/m3", ACCENTS["pm25"]), unsafe_allow_html=True)
    p2.markdown(metric_card("NO2", str(main_row["no2"]), "ug/m3", ACCENTS["no2"]), unsafe_allow_html=True)
    p3, p4 = st.columns(2)
    p3.markdown(metric_card("Wind", str(main_row["wind_speed_mps"]), "m/s", ACCENTS["wind"]), unsafe_allow_html=True)
    p4.markdown(metric_card("Plume", str(main_row["plume_pm25"]), "ug/m3", ACCENTS["plume"]), unsafe_allow_html=True)
    st.markdown(driver_breakdown(main_row), unsafe_allow_html=True)
    st.markdown(recommendation_card(str(main_row.get("health_text") or "")), unsafe_allow_html=True)
    st.markdown("<div style='margin:13px 0 2px'></div>", unsafe_allow_html=True)
    st.markdown(section_label("Top 5 risk districts"), unsafe_allow_html=True)
    top5_html = "".join(
        top5_row(idx, str(row["district_name"]), int(row["aqi"]))
        for idx, row in enumerate(top_n_worst(bundle, 5), 1)
    )
    st.markdown(
        f'<div style="background:rgba(255,255,255,.035);border:1px solid rgba(230,238,232,.105);'
        f'border-radius:8px;padding:13px 14px">{top5_html}</div>',
        unsafe_allow_html=True,
    )

st.markdown("<div style='margin-top:17px'></div>", unsafe_allow_html=True)
st.markdown(section_label("24-hour trajectory"), unsafe_allow_html=True)
_chart(bundle, selected_district, selected_label, main_row, hour)
