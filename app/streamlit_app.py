from __future__ import annotations

import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

import streamlit as st

from hanoi_air.config import get_settings
from hanoi_air.forecast import build_cached_forecast, top_n_worst
from hanoi_air.geography import load_districts
from hanoi_air.observability import init_sentry
from hanoi_air.validation import load_latest_backtest
from hanoi_air.viz import aqi_color, build_folium_map
from hanoi_air.vn_aqi import vn_aqi_category, vn_aqi_color

init_sentry(service="dashboard")

st.set_page_config(
    page_title="Hanoi Air Forecast",
    page_icon="🌫️",
    layout="wide",
    initial_sidebar_state="expanded",
)

# ── Global CSS ────────────────────────────────────────────────────────────────
st.markdown("""
<style>
@import url('https://fonts.googleapis.com/css2?family=Inter:wght@300;400;500;600;700;800&display=swap');

*, *::before, *::after { box-sizing: border-box; }

html, body, .stApp {
    font-family: 'Inter', -apple-system, BlinkMacSystemFont, sans-serif !important;
    background: #080d1a !important;
    color: #e2e8f0 !important;
}

#MainMenu, footer { visibility: hidden; }
.stDeployButton { display: none !important; }
.block-container { padding: 1.2rem 1.8rem 2rem !important; max-width: 100% !important; }

/* Sidebar */
[data-testid="stSidebar"] {
    background: linear-gradient(180deg, #0d1526 0%, #080d1a 100%) !important;
    border-right: 1px solid rgba(255,255,255,0.06) !important;
}
[data-testid="stSidebar"] > div { padding-top: 1rem; }

/* Sidebar labels */
[data-testid="stSidebar"] label,
[data-testid="stSidebar"] .stSlider label,
[data-testid="stSidebar"] p {
    color: #94a3b8 !important;
    font-size: 0.78rem !important;
    text-transform: uppercase;
    letter-spacing: 0.07em;
}
[data-testid="stSidebar"] h1 {
    color: #f1f5f9 !important;
    font-size: 1.2rem !important;
    font-weight: 700 !important;
    letter-spacing: -0.02em;
}

/* Buttons */
.stButton > button {
    background: rgba(99,179,237,0.08) !important;
    border: 1px solid rgba(99,179,237,0.25) !important;
    color: #93c5fd !important;
    border-radius: 9px !important;
    font-size: 0.85rem !important;
    font-weight: 500 !important;
    transition: all 0.18s ease !important;
    padding: 0.45rem 1rem !important;
}
.stButton > button:hover {
    background: rgba(99,179,237,0.16) !important;
    border-color: rgba(99,179,237,0.5) !important;
    transform: translateY(-1px);
    box-shadow: 0 4px 15px rgba(99,179,237,0.15) !important;
}

/* Toggle */
[data-testid="stToggle"] { margin: 4px 0 !important; }

/* Selectbox */
[data-testid="stSelectbox"] > div > div {
    background: rgba(255,255,255,0.04) !important;
    border: 1px solid rgba(255,255,255,0.1) !important;
    border-radius: 9px !important;
    color: #e2e8f0 !important;
}

/* Slider */
[data-testid="stSlider"] [data-baseweb="slider"] div[role="slider"] {
    background: #63b3ed !important;
    border-color: #63b3ed !important;
}
[data-testid="stSlider"] [data-baseweb="slider"] > div > div > div {
    background: linear-gradient(90deg, #63b3ed, #a78bfa) !important;
}

/* Native metric containers */
[data-testid="metric-container"] {
    background: rgba(255,255,255,0.04) !important;
    border: 1px solid rgba(255,255,255,0.08) !important;
    border-radius: 12px !important;
    padding: 14px 18px !important;
    transition: border-color 0.2s;
}
[data-testid="metric-container"]:hover { border-color: rgba(99,179,237,0.25) !important; }
[data-testid="stMetricLabel"] p {
    color: #64748b !important;
    font-size: 0.68rem !important;
    text-transform: uppercase !important;
    letter-spacing: 0.09em !important;
}
[data-testid="stMetricValue"] {
    color: #f1f5f9 !important;
    font-size: 1.55rem !important;
    font-weight: 700 !important;
}

/* Tabs */
[data-testid="stTabs"] [data-baseweb="tab-list"] {
    background: rgba(255,255,255,0.04) !important;
    border-radius: 10px !important;
    padding: 3px !important;
    gap: 2px !important;
    border: 1px solid rgba(255,255,255,0.07) !important;
}
[data-testid="stTabs"] [data-baseweb="tab"] {
    border-radius: 7px !important;
    color: #64748b !important;
    font-size: 0.82rem !important;
    font-weight: 500 !important;
    padding: 5px 18px !important;
    background: transparent !important;
}
[data-testid="stTabs"] [aria-selected="true"] {
    background: rgba(99,179,237,0.12) !important;
    color: #93c5fd !important;
}

/* Dataframe */
[data-testid="stDataFrame"] > div {
    background: rgba(255,255,255,0.02) !important;
    border: 1px solid rgba(255,255,255,0.07) !important;
    border-radius: 10px !important;
}

/* Divider */
hr { border-color: rgba(255,255,255,0.06) !important; margin: 10px 0 !important; }

/* Map iframe */
iframe {
    border-radius: 14px !important;
    border: 1px solid rgba(255,255,255,0.08) !important;
}

/* Alerts */
[data-testid="stAlert"] {
    background: rgba(239,68,68,0.08) !important;
    border: 1px solid rgba(239,68,68,0.25) !important;
    border-radius: 10px !important;
}
[data-testid="stAlert"] p { color: #fca5a5 !important; }

/* Line chart */
[data-testid="stArrowVegaLiteChart"] { border-radius: 12px !important; overflow: hidden; }

/* Plotly chart bg */
.js-plotly-plot { border-radius: 12px !important; }
</style>
""", unsafe_allow_html=True)


# ── Helpers ───────────────────────────────────────────────────────────────────
def _aqi_label_color(aqi: int) -> tuple[str, str]:
    if aqi <= 50:   return "Tốt", "#22c55e"
    if aqi <= 100:  return "Trung bình", "#eab308"
    if aqi <= 150:  return "Không tốt", "#f97316"
    if aqi <= 200:  return "Xấu", "#ef4444"
    if aqi <= 300:  return "Rất xấu", "#a855f7"
    return "Nguy hiểm", "#7f1d1d"


def _metric_card(label: str, value: str, unit: str = "", accent: str = "#63b3ed") -> str:
    return f"""
    <div style="
        background:rgba(255,255,255,0.04);
        border:1px solid rgba(255,255,255,0.08);
        border-radius:12px;
        padding:14px 18px;
        text-align:center;
        transition:border-color .2s;
    ">
        <div style="color:#64748b;font-size:.68rem;text-transform:uppercase;letter-spacing:.09em;margin-bottom:5px">{label}</div>
        <div style="color:{accent};font-size:1.55rem;font-weight:700;line-height:1.1">{value}</div>
        {f'<div style="color:#475569;font-size:.72rem;margin-top:3px">{unit}</div>' if unit else ''}
    </div>"""


def _aqi_hero_card(aqi: int, category: str, color: str) -> str:
    return f"""
    <div style="
        background:linear-gradient(135deg,{color}20,{color}08);
        border:1px solid {color}40;
        border-radius:16px;
        padding:22px 20px 18px;
        text-align:center;
        box-shadow:0 0 35px {color}18;
        margin-bottom:14px;
    ">
        <div style="color:#64748b;font-size:.65rem;text-transform:uppercase;letter-spacing:.12em;margin-bottom:8px">Chỉ số AQI</div>
        <div style="font-size:3.2rem;font-weight:800;color:{color};line-height:1;
                    text-shadow:0 0 25px {color}66;letter-spacing:-0.02em">{aqi}</div>
        <div style="display:inline-block;background:{color}22;border:1px solid {color}44;
                    border-radius:20px;padding:3px 14px;font-size:.82rem;color:{color};
                    font-weight:600;margin-top:10px">{category}</div>
    </div>"""


def _source_badge(mode: str) -> str:
    cfg = {
        "live":                ("🟢", "LIVE",       "#22c55e"),
        "free_api_background": ("🟡", "BACKGROUND", "#eab308"),
        "sample":              ("⚪", "SAMPLE",      "#64748b"),
    }.get(mode, ("⚪", mode.upper(), "#64748b"))
    icon, label, color = cfg
    return f"""
    <span style="display:inline-flex;align-items:center;gap:5px;
        background:{color}15;border:1px solid {color}35;
        border-radius:20px;padding:3px 11px;
        font-size:.72rem;font-weight:600;color:{color};letter-spacing:.05em">
        {icon} {label}
    </span>"""


def _top5_row(rank: int, name: str, aqi: int, color: str) -> str:
    bar = min(100, int(aqi / 3))
    return f"""
    <div style="margin-bottom:10px">
        <div style="display:flex;justify-content:space-between;align-items:center;margin-bottom:4px">
            <span style="color:#94a3b8;font-size:.8rem">
                <span style="color:{color};font-weight:700;margin-right:6px">#{rank}</span>{name}
            </span>
            <span style="color:{color};font-weight:700;font-size:.85rem">{aqi}</span>
        </div>
        <div style="height:4px;background:rgba(255,255,255,0.06);border-radius:2px">
            <div style="height:100%;width:{bar}%;background:{color};border-radius:2px;
                        box-shadow:0 0 6px {color}66"></div>
        </div>
    </div>"""


# ── Data ─────────────────────────────────────────────────────────────────────
@st.cache_data(ttl=1800, show_spinner=False)
def _load_bundle(use_live: bool, force: bool) -> dict:
    return build_cached_forecast(get_settings(), force_refresh=force, use_live=use_live)


districts = load_districts()
district_options = {"Toàn Hà Nội": None}
district_options.update({d.name: d.district_id for d in districts})

# ── Sidebar ───────────────────────────────────────────────────────────────────
with st.sidebar:
    st.markdown("""
    <div style="display:flex;align-items:center;gap:10px;margin-bottom:4px">
        <div style="width:32px;height:32px;background:linear-gradient(135deg,#3b82f6,#a78bfa);
                    border-radius:8px;display:flex;align-items:center;justify-content:center;
                    font-size:16px">🌫️</div>
        <div>
            <div style="color:#f1f5f9;font-size:1.05rem;font-weight:700;letter-spacing:-0.01em">Hanoi Air</div>
            <div style="color:#475569;font-size:.68rem;margin-top:-1px">Forecast Dashboard</div>
        </div>
    </div>
    """, unsafe_allow_html=True)
    st.divider()
    use_live = st.toggle("🔴 Live data", value=True)
    force_refresh = st.button("↺  Refresh ngay", use_container_width=True)
    st.divider()
    hour = st.slider("Giờ dự báo", 0, 23, 0, format="T+%dh")
    selected_label = st.selectbox("Quận / huyện", list(district_options.keys()))
    selected_district = district_options[selected_label]
    show_downwind = st.toggle("💨 Hiển thị vùng xuôi gió", value=True)
    st.divider()
    st.markdown(
        '<div style="color:#334155;font-size:.68rem;line-height:1.6">'
        'Nguồn dữ liệu<br>'
        '<span style="color:#475569">AQICN · OpenAQ · Open-Meteo</span>'
        '</div>',
        unsafe_allow_html=True,
    )

# ── Load bundle ───────────────────────────────────────────────────────────────
with st.spinner(""):
    bundle = _load_bundle(use_live, force_refresh)

hour_rows = [r for r in bundle["forecasts"] if int(r["hour_offset"]) == hour]
selected_rows = [r for r in hour_rows if selected_district is None or r["district_id"] == selected_district]
main_row = max(selected_rows or hour_rows, key=lambda r: int(r["aqi"]))
aqi_val = int(main_row["aqi"])
_, aqi_clr = _aqi_label_color(aqi_val)

# ── Page title row ────────────────────────────────────────────────────────────
title_col, badge_col = st.columns([5, 1])
with title_col:
    st.markdown(
        f'<h1 style="margin:0;font-size:1.45rem;font-weight:700;color:#f1f5f9;letter-spacing:-0.02em">'
        f'Hà Nội — Dự báo chất lượng không khí 24h</h1>'
        f'<div style="color:#475569;font-size:.78rem;margin-top:3px">Cập nhật mỗi 30 phút · {bundle.get("generated_at","")[:16].replace("T"," ")} UTC</div>',
        unsafe_allow_html=True,
    )
with badge_col:
    st.markdown(
        f'<div style="text-align:right;padding-top:6px">{_source_badge(bundle["mode"])}</div>',
        unsafe_allow_html=True,
    )

st.markdown("<div style='margin-bottom:10px'></div>", unsafe_allow_html=True)

# ── KPI cards row ─────────────────────────────────────────────────────────────
k1, k2, k3, k4, k5 = st.columns(5)
k1.markdown(_metric_card("Max AQI hôm nay", str(bundle["max_aqi"]), accent=aqi_clr), unsafe_allow_html=True)
k2.markdown(_metric_card("PM2.5 điểm nóng", f"{main_row['pm25']}", "µg/m³", "#f97316"), unsafe_allow_html=True)
k3.markdown(_metric_card("NO₂ điểm nóng", f"{main_row['no2']}", "µg/m³", "#a78bfa"), unsafe_allow_html=True)
k4.markdown(_metric_card("Cảnh báo", str(len(bundle["alerts"])), "quận vượt ngưỡng", "#ef4444" if bundle["alerts"] else "#22c55e"), unsafe_allow_html=True)
k5.markdown(_metric_card("Đang xem", f"T+{hour}h", f"{selected_label}", "#63b3ed"), unsafe_allow_html=True)

st.markdown("<div style='margin-bottom:6px'></div>", unsafe_allow_html=True)

# ── Alert banner ──────────────────────────────────────────────────────────────
if bundle["alerts"]:
    alert_msgs = " · ".join(a["message"][:60] for a in bundle["alerts"][:3])
    st.markdown(
        f'<div style="background:rgba(239,68,68,.08);border:1px solid rgba(239,68,68,.25);'
        f'border-radius:10px;padding:9px 16px;font-size:.8rem;color:#fca5a5;margin-bottom:8px">'
        f'⚠️ &nbsp;<b>{len(bundle["alerts"])} cảnh báo</b> — {alert_msgs}{"..." if len(bundle["alerts"])>3 else ""}'
        f'</div>',
        unsafe_allow_html=True,
    )

# ── Main layout ───────────────────────────────────────────────────────────────
map_col, info_col = st.columns([2.5, 1.0])

with map_col:
    tab_map, tab_table = st.tabs(["🗺️  Bản đồ", "📊  Bảng dữ liệu"])

    with tab_map:
        map_obj = build_folium_map(
            bundle, hour_offset=hour,
            selected_district=selected_district,
            show_downwind=show_downwind,
        )
        if map_obj is None:
            st.error("Cần cài: `pip install folium streamlit-folium`")
        else:
            try:
                from streamlit_folium import st_folium  # type: ignore
                st_folium(map_obj, width=None, height=590,
                          returned_objects=[],
                          key=f"map_v4_{hour}_{selected_district}_{int(show_downwind)}")
            except Exception:
                st.components.v1.html(map_obj._repr_html_(), height=590)

        # Map legend
        st.markdown("""
        <div style="display:flex;gap:10px;flex-wrap:wrap;margin-top:8px;padding:8px 12px;
                    background:rgba(255,255,255,0.03);border-radius:8px;border:1px solid rgba(255,255,255,0.06)">
            <span style="font-size:.7rem;color:#475569;margin-right:4px">AQI:</span>
            <span style="font-size:.7rem;color:#22c55e">● Tốt ≤50</span>
            <span style="font-size:.7rem;color:#eab308">● TB ≤100</span>
            <span style="font-size:.7rem;color:#f97316">● Không tốt ≤150</span>
            <span style="font-size:.7rem;color:#ef4444">● Xấu ≤200</span>
            <span style="font-size:.7rem;color:#a855f7">● Rất xấu ≤300</span>
        </div>""", unsafe_allow_html=True)

    with tab_table:
        try:
            import pandas as pd
            df = pd.DataFrame(hour_rows)[[
                "district_name", "aqi", "pm25", "no2", "category",
                "wind_speed_mps", "uncertainty_low", "uncertainty_high",
            ]].sort_values("aqi", ascending=False).rename(columns={
                "district_name": "Quận", "aqi": "AQI", "pm25": "PM2.5 µg/m³",
                "no2": "NO2 µg/m³", "category": "Mức độ",
                "wind_speed_mps": "Gió m/s",
                "uncertainty_low": "AQI min", "uncertainty_high": "AQI max",
            })
            st.dataframe(df, use_container_width=True, hide_index=True, height=560)
        except Exception:
            st.json(hour_rows[:12])

with info_col:
    # AQI hero
    cat, clr = _aqi_label_color(aqi_val)
    label = selected_label if selected_label != "Toàn Hà Nội" else main_row["district_name"]
    st.markdown(f'<div style="color:#94a3b8;font-size:.72rem;margin-bottom:6px;'
                f'text-transform:uppercase;letter-spacing:.07em">📍 {label}</div>',
                unsafe_allow_html=True)
    st.markdown(_aqi_hero_card(aqi_val, cat, clr), unsafe_allow_html=True)

    # Detail metrics
    d1, d2 = st.columns(2)
    d1.markdown(_metric_card("PM2.5", str(main_row["pm25"]), "µg/m³", "#f97316"), unsafe_allow_html=True)
    d2.markdown(_metric_card("NO₂", str(main_row["no2"]), "µg/m³", "#a78bfa"), unsafe_allow_html=True)
    st.markdown("<div style='margin:6px 0'></div>", unsafe_allow_html=True)
    d3, d4 = st.columns(2)
    d3.markdown(_metric_card("Gió", f"{main_row['wind_speed_mps']}", "m/s", "#63b3ed"), unsafe_allow_html=True)
    d4.markdown(_metric_card("Plume", f"{main_row['plume_pm25']}", "µg/m³", "#94a3b8"), unsafe_allow_html=True)

    st.markdown(
        f'<div style="background:rgba(255,255,255,0.03);border:1px solid rgba(255,255,255,0.07);'
        f'border-radius:10px;padding:10px 12px;font-size:.75rem;color:#64748b;'
        f'line-height:1.55;margin-top:8px">{main_row["health_text"]}</div>',
        unsafe_allow_html=True,
    )

    st.markdown("<div style='margin:12px 0 6px'></div>", unsafe_allow_html=True)
    st.markdown(
        '<div style="color:#94a3b8;font-size:.72rem;text-transform:uppercase;'
        'letter-spacing:.07em;margin-bottom:8px">🏆 Top 5 ô nhiễm nhất</div>',
        unsafe_allow_html=True,
    )
    top5_html = ""
    for i, row in enumerate(top_n_worst(bundle, 5), 1):
        _, c = _aqi_label_color(int(row["aqi"]))
        top5_html += _top5_row(i, row["district_name"], int(row["aqi"]), c)
    st.markdown(
        f'<div style="background:rgba(255,255,255,0.03);border:1px solid rgba(255,255,255,0.07);'
        f'border-radius:12px;padding:14px 16px">{top5_html}</div>',
        unsafe_allow_html=True,
    )

# ── 24h Forecast chart ────────────────────────────────────────────────────────
st.markdown("<div style='margin-top:18px'></div>", unsafe_allow_html=True)
st.markdown(
    '<div style="color:#94a3b8;font-size:.72rem;text-transform:uppercase;'
    'letter-spacing:.07em;margin-bottom:8px">📈 Diễn biến 24 giờ</div>',
    unsafe_allow_html=True,
)

try:
    import pandas as pd
    import plotly.graph_objects as go

    if selected_district:
        series = [r for r in bundle["forecasts"] if r["district_id"] == selected_district]
        title_str = selected_label
    else:
        series = [r for r in bundle["forecasts"] if r["district_id"] == main_row["district_id"]]
        title_str = main_row["district_name"] + " (điểm nóng nhất)"

    df_chart = pd.DataFrame(series).sort_values("hour_offset")

    fig = go.Figure()

    # AQI zone bands
    for y0, y1, color in [(0,50,"#22c55e"),(50,100,"#eab308"),(100,150,"#f97316"),(150,200,"#ef4444"),(200,300,"#a855f7")]:
        fig.add_hrect(y0=y0, y1=y1, fillcolor=color, opacity=0.04, line_width=0)

    # Uncertainty band
    fig.add_trace(go.Scatter(
        x=list(df_chart["hour_offset"]) + list(df_chart["hour_offset"])[::-1],
        y=list(df_chart["uncertainty_high"]) + list(df_chart["uncertainty_low"])[::-1],
        fill="toself", fillcolor="rgba(99,179,237,0.07)",
        line=dict(width=0), showlegend=False, hoverinfo="skip",
    ))

    # AQI line
    fig.add_trace(go.Scatter(
        x=df_chart["hour_offset"], y=df_chart["aqi"],
        name="AQI", mode="lines+markers",
        line=dict(color="#ef4444", width=2.5),
        marker=dict(size=5, color="#ef4444"),
        hovertemplate="T+%{x}h — AQI: <b>%{y}</b><extra></extra>",
    ))

    # PM2.5 line
    fig.add_trace(go.Scatter(
        x=df_chart["hour_offset"], y=df_chart["pm25"],
        name="PM2.5 µg/m³", mode="lines",
        line=dict(color="#f97316", width=1.8, dash="dot"),
        yaxis="y2",
        hovertemplate="PM2.5: <b>%{y:.1f}</b> µg/m³<extra></extra>",
    ))

    # NO2 line
    fig.add_trace(go.Scatter(
        x=df_chart["hour_offset"], y=df_chart["no2"],
        name="NO₂ µg/m³", mode="lines",
        line=dict(color="#a78bfa", width=1.8, dash="dot"),
        yaxis="y2",
        hovertemplate="NO₂: <b>%{y:.1f}</b> µg/m³<extra></extra>",
    ))

    # Current hour marker
    fig.add_vline(x=hour, line_color="rgba(255,255,255,0.2)", line_dash="dash", line_width=1)

    fig.update_layout(
        paper_bgcolor="rgba(0,0,0,0)",
        plot_bgcolor="rgba(255,255,255,0.02)",
        font=dict(color="#94a3b8", family="Inter", size=11),
        height=280,
        margin=dict(l=0, r=0, t=10, b=0),
        hovermode="x unified",
        legend=dict(
            bgcolor="rgba(15,20,35,0.8)", bordercolor="rgba(255,255,255,0.08)",
            borderwidth=1, font=dict(size=11), x=0.01, y=0.99,
        ),
        xaxis=dict(
            title="Giờ dự báo (T+h)",
            gridcolor="rgba(255,255,255,0.05)", zeroline=False,
            tickfont=dict(color="#475569"),
            title_font=dict(color="#64748b", size=10),
        ),
        yaxis=dict(
            title="AQI",
            gridcolor="rgba(255,255,255,0.05)", zeroline=False,
            tickfont=dict(color="#475569"),
            title_font=dict(color="#64748b", size=10),
        ),
        yaxis2=dict(
            title="µg/m³", overlaying="y", side="right",
            gridcolor="rgba(0,0,0,0)", zeroline=False,
            tickfont=dict(color="#475569"),
            title_font=dict(color="#64748b", size=10),
        ),
    )
    st.plotly_chart(fig, use_container_width=True, config={"displayModeBar": False})

except Exception as exc:
    st.warning(f"Không vẽ được chart: {exc}")

# ── VN AQI + Source Attribution tabs ──────────────────────────────────────────
st.markdown("<div style='margin-top:22px'></div>", unsafe_allow_html=True)
tab_vn_aqi, tab_sources, tab_actions, tab_accuracy = st.tabs(
    ["🇻🇳  VN_AQI (QCVN)", "🥧  Nguồn ô nhiễm", "✅  Hành động", "📐  Độ chính xác"]
)

with tab_vn_aqi:
    st.markdown(
        '<div style="color:#94a3b8;font-size:.72rem;text-transform:uppercase;'
        'letter-spacing:.07em;margin-bottom:10px">'
        'Chuẩn Việt Nam — QCVN 06:2022 / Quyết định 1459/QĐ-TCMT 2019'
        '</div>',
        unsafe_allow_html=True,
    )

    vn_aqi_val = int(main_row.get("vn_aqi", 0))
    vn_cat = main_row.get("vn_category") or vn_aqi_category(vn_aqi_val)
    vn_clr = vn_aqi_color(vn_aqi_val)

    hero_col, table_col = st.columns([1, 2])
    with hero_col:
        st.markdown(_aqi_hero_card(vn_aqi_val, vn_cat, vn_clr), unsafe_allow_html=True)
        us_aqi_val = int(main_row["aqi"])
        delta = vn_aqi_val - us_aqi_val
        delta_color = "#ef4444" if delta > 0 else "#22c55e" if delta < 0 else "#64748b"
        delta_sign = "+" if delta > 0 else ""
        st.markdown(
            f'<div style="background:rgba(255,255,255,0.03);'
            f'border:1px solid rgba(255,255,255,0.07);border-radius:10px;'
            f'padding:10px 14px;text-align:center;font-size:.78rem;color:#94a3b8">'
            f'So với US-EPA: <b style="color:{delta_color}">{delta_sign}{delta}</b><br>'
            f'<span style="color:#475569;font-size:.7rem">'
            f'(US-EPA {us_aqi_val} · VN_AQI {vn_aqi_val})</span>'
            f'</div>',
            unsafe_allow_html=True,
        )

    with table_col:
        try:
            import pandas as pd
            comparison_rows = []
            for r in hour_rows:
                comparison_rows.append({
                    "Quận": r["district_name"],
                    "PM2.5 µg/m³": r["pm25"],
                    "US-EPA AQI": r["aqi"],
                    "US-EPA mức độ": r["category"],
                    "VN_AQI": int(r.get("vn_aqi", 0)),
                    "VN mức độ": r.get("vn_category", ""),
                })
            df_vn = pd.DataFrame(comparison_rows).sort_values("VN_AQI", ascending=False)
            st.dataframe(df_vn, use_container_width=True, hide_index=True, height=420)
        except Exception as exc:
            st.warning(f"Không hiển thị bảng so sánh: {exc}")

    st.markdown(
        '<div style="color:#475569;font-size:.7rem;line-height:1.55;margin-top:8px">'
        'VN_AQI dùng ngưỡng PM2.5 24h (0–25 Tốt · 25–50 Trung bình · 50–80 Kém · '
        '80–150 Xấu · 150–250 Rất xấu · ≥250 Nguy hại). '
        'US-EPA NowCast nghiêm khắc hơn ở dải PM2.5 thấp nên giá trị thường lớn hơn.'
        '</div>',
        unsafe_allow_html=True,
    )

with tab_sources:
    st.markdown(
        '<div style="color:#94a3b8;font-size:.72rem;text-transform:uppercase;'
        'letter-spacing:.07em;margin-bottom:10px">'
        f'Phân bổ nguồn PM2.5 — {main_row["district_name"]} · T+{hour}h'
        '</div>',
        unsafe_allow_html=True,
    )

    breakdown = main_row.get("source_breakdown") or {}
    SOURCE_LABELS = {
        "traffic": ("Giao thông", "#f97316"),
        "industry": ("Công nghiệp", "#a78bfa"),
        "agriculture": ("Nông nghiệp / đốt", "#84cc16"),
        "fire": ("Cháy rừng", "#ef4444"),
        "other": ("Khác / nền", "#64748b"),
    }

    try:
        import pandas as pd
        import plotly.graph_objects as go

        pie_col, stack_col = st.columns([1, 1.4])
        with pie_col:
            labels = [SOURCE_LABELS[k][0] for k in SOURCE_LABELS if k in breakdown]
            values = [float(breakdown.get(k, 0.0)) for k in SOURCE_LABELS if k in breakdown]
            colors = [SOURCE_LABELS[k][1] for k in SOURCE_LABELS if k in breakdown]
            if sum(values) > 0:
                pie = go.Figure(go.Pie(
                    labels=labels, values=values, hole=0.55,
                    marker=dict(colors=colors, line=dict(color="#080d1a", width=2)),
                    textinfo="label+percent", textfont=dict(color="#e2e8f0", size=11),
                    hovertemplate="%{label}: <b>%{percent}</b><extra></extra>",
                ))
                pie.update_layout(
                    paper_bgcolor="rgba(0,0,0,0)",
                    plot_bgcolor="rgba(0,0,0,0)",
                    font=dict(color="#94a3b8", family="Inter"),
                    height=320,
                    margin=dict(l=0, r=0, t=10, b=10),
                    showlegend=False,
                )
                st.plotly_chart(pie, use_container_width=True, config={"displayModeBar": False})
            else:
                st.info("Chưa có phân bổ nguồn cho giờ này.")

        with stack_col:
            district_id_for_stack = main_row["district_id"]
            series_rows = [
                r for r in bundle["forecasts"]
                if r["district_id"] == district_id_for_stack
            ]
            series_rows.sort(key=lambda r: int(r["hour_offset"]))
            hours = [int(r["hour_offset"]) for r in series_rows]
            stack = go.Figure()
            for key, (label, color) in SOURCE_LABELS.items():
                ys = [float((r.get("source_breakdown") or {}).get(key, 0.0)) * 100 for r in series_rows]
                stack.add_trace(go.Bar(
                    x=hours, y=ys, name=label,
                    marker=dict(color=color, line=dict(width=0)),
                    hovertemplate=f"{label}: <b>%{{y:.1f}}%</b><extra></extra>",
                ))
            stack.add_vline(x=hour, line_color="rgba(255,255,255,0.25)",
                            line_dash="dash", line_width=1)
            stack.update_layout(
                barmode="stack",
                paper_bgcolor="rgba(0,0,0,0)",
                plot_bgcolor="rgba(255,255,255,0.02)",
                font=dict(color="#94a3b8", family="Inter", size=11),
                height=320,
                margin=dict(l=0, r=0, t=10, b=0),
                hovermode="x unified",
                legend=dict(
                    bgcolor="rgba(15,20,35,0.8)",
                    bordercolor="rgba(255,255,255,0.08)",
                    borderwidth=1, font=dict(size=10),
                    orientation="h", y=-0.18, x=0,
                ),
                xaxis=dict(
                    title="Giờ dự báo (T+h)",
                    gridcolor="rgba(255,255,255,0.05)", zeroline=False,
                    tickfont=dict(color="#475569"),
                    title_font=dict(color="#64748b", size=10),
                ),
                yaxis=dict(
                    title="% PM2.5", range=[0, 100],
                    gridcolor="rgba(255,255,255,0.05)", zeroline=False,
                    tickfont=dict(color="#475569"),
                    title_font=dict(color="#64748b", size=10),
                ),
            )
            st.plotly_chart(stack, use_container_width=True, config={"displayModeBar": False})

        if breakdown:
            top_key = max(breakdown, key=lambda k: breakdown.get(k, 0.0))
            top_label, top_color = SOURCE_LABELS.get(top_key, (top_key, "#94a3b8"))
            top_share = breakdown.get(top_key, 0.0)
            st.markdown(
                f'<div style="background:rgba(255,255,255,0.03);'
                f'border:1px solid {top_color}33;border-radius:10px;'
                f'padding:10px 14px;margin-top:6px;font-size:.78rem;color:#94a3b8">'
                f'Nguồn chính: <b style="color:{top_color}">{top_label}</b> '
                f'({top_share*100:.1f} %) — '
                f'{"hành động: hạn chế xe cá nhân giờ cao điểm" if top_key=="traffic" else ""}'
                f'{"hành động: kiểm tra nhà máy xuôi gió" if top_key=="industry" else ""}'
                f'{"hành động: ngăn đốt rơm rạ" if top_key=="agriculture" else ""}'
                f'{"hành động: theo dõi vệt khói khu vực" if top_key=="fire" else ""}'
                f'</div>',
                unsafe_allow_html=True,
            )
    except Exception as exc:
        st.warning(f"Không vẽ được phân bổ nguồn: {exc}")

with tab_actions:
    st.markdown(
        '<div style="color:#94a3b8;font-size:.72rem;text-transform:uppercase;'
        'letter-spacing:.07em;margin-bottom:10px">'
        f'Khuyến nghị cho {main_row["district_name"]} · T+{hour}h '
        f'· AQI {int(main_row["aqi"])} ({main_row["category"]})'
        '</div>',
        unsafe_allow_html=True,
    )

    actions = main_row.get("actions") or {}
    citizen = actions.get("citizen", [])
    gov = actions.get("government", [])

    col_citizen, col_gov = st.columns(2)
    with col_citizen:
        st.markdown(
            '<div style="color:#63b3ed;font-size:.82rem;font-weight:600;'
            'margin-bottom:6px">👤 Cho người dân</div>',
            unsafe_allow_html=True,
        )
        if not citizen:
            st.markdown(
                '<div style="color:#475569;font-size:.78rem;padding:10px 14px;'
                'background:rgba(255,255,255,0.03);border:1px solid rgba(255,255,255,0.06);'
                'border-radius:10px">Không có khuyến nghị đặc biệt.</div>',
                unsafe_allow_html=True,
            )
        for item in citizen:
            st.markdown(
                f'<div style="background:rgba(99,179,237,0.08);'
                f'border:1px solid rgba(99,179,237,0.25);border-left:3px solid #63b3ed;'
                f'border-radius:8px;padding:8px 12px;margin-bottom:6px;'
                f'font-size:.82rem;color:#cbd5e1">{item}</div>',
                unsafe_allow_html=True,
            )

    with col_gov:
        st.markdown(
            '<div style="color:#f59e0b;font-size:.82rem;font-weight:600;'
            'margin-bottom:6px">🏛️ Cho chính quyền</div>',
            unsafe_allow_html=True,
        )
        if not gov:
            st.markdown(
                '<div style="color:#475569;font-size:.78rem;padding:10px 14px;'
                'background:rgba(255,255,255,0.03);border:1px solid rgba(255,255,255,0.06);'
                'border-radius:10px">Mức AQI hiện tại chưa cần can thiệp.</div>',
                unsafe_allow_html=True,
            )
        for item in gov:
            st.markdown(
                f'<div style="background:rgba(245,158,11,0.08);'
                f'border:1px solid rgba(245,158,11,0.25);border-left:3px solid #f59e0b;'
                f'border-radius:8px;padding:8px 12px;margin-bottom:6px;'
                f'font-size:.82rem;color:#cbd5e1">{item}</div>',
                unsafe_allow_html=True,
            )

    # Fire-origin alerts (if any) get a distinct banner.
    fire_alerts = [a for a in bundle.get("alerts", []) if a.get("pollutant") == "FIRE_PM25"]
    if fire_alerts:
        st.markdown(
            '<div style="margin-top:14px;color:#fca5a5;font-size:.78rem;'
            'font-weight:600">🔥 Cảnh báo cháy ngoại biên</div>',
            unsafe_allow_html=True,
        )
        for fa in fire_alerts:
            st.markdown(
                f'<div style="background:rgba(239,68,68,0.08);'
                f'border:1px solid rgba(239,68,68,0.3);border-left:3px solid #ef4444;'
                f'border-radius:8px;padding:8px 12px;margin-top:6px;'
                f'font-size:.82rem;color:#fca5a5">{fa["message"]}</div>',
                unsafe_allow_html=True,
            )

with tab_accuracy:
    st.markdown(
        '<div style="color:#94a3b8;font-size:.72rem;text-transform:uppercase;'
        'letter-spacing:.07em;margin-bottom:10px">'
        'Backtest dự báo PM2.5 vs trạm quan trắc'
        '</div>',
        unsafe_allow_html=True,
    )

    snapshot = load_latest_backtest(get_settings())
    if snapshot is None:
        st.info(
            "Chưa có snapshot backtest. Chạy `python scripts/run_backtest.py --days 7` "
            "sau khi có ít nhất một chu kỳ live ingestion."
        )
    elif snapshot.get("status") != "ok":
        st.warning(
            f"Backtest status: **{snapshot.get('status')}** — "
            f"{snapshot.get('note', '')}"
        )
    else:
        overall = snapshot["overall"]
        fc = overall.get("forecast", {})
        base = overall.get("persistence_baseline", {})
        improvement = overall.get("rmse_improvement_vs_persistence")

        m1, m2, m3, m4 = st.columns(4)
        m1.markdown(
            _metric_card("Forecast RMSE", str(fc.get("rmse", "—")), "µg/m³", "#63b3ed"),
            unsafe_allow_html=True,
        )
        m2.markdown(
            _metric_card("Forecast MAE", str(fc.get("mae", "—")), "µg/m³", "#a78bfa"),
            unsafe_allow_html=True,
        )
        m3.markdown(
            _metric_card("Forecast R²", str(fc.get("r2", "—")), "", "#22c55e"),
            unsafe_allow_html=True,
        )
        improvement_value = f"{improvement:+}" if improvement is not None else "—"
        improvement_color = (
            "#22c55e" if (improvement or 0) > 0 else "#ef4444" if (improvement or 0) < 0 else "#64748b"
        )
        m4.markdown(
            _metric_card("Tốt hơn persistence", improvement_value, "µg/m³ RMSE", improvement_color),
            unsafe_allow_html=True,
        )

        st.markdown(
            f'<div style="color:#475569;font-size:.72rem;margin-top:8px">'
            f'Mẫu: {fc.get("n", 0)} cặp dự báo/đo · '
            f'Persistence baseline RMSE {base.get("rmse", "—")} µg/m³ · '
            f'Sinh lúc {snapshot.get("generated_at", "")[:16].replace("T", " ")}'
            f'</div>',
            unsafe_allow_html=True,
        )

        try:
            import pandas as pd
            df_acc = pd.DataFrame(snapshot.get("per_district", []))
            if not df_acc.empty:
                df_acc = df_acc.rename(columns={
                    "district_id": "Quận",
                    "actual_pm25": "Đo thực (µg/m³)",
                    "forecast_pm25": "Dự báo (µg/m³)",
                    "persistence_pm25": "Persistence (µg/m³)",
                    "abs_error": "|Sai số dự báo|",
                    "persistence_abs_error": "|Sai số persistence|",
                }).sort_values("|Sai số dự báo|", ascending=False)
                st.dataframe(df_acc, use_container_width=True, hide_index=True, height=380)
        except Exception as exc:
            st.warning(f"Không hiển thị bảng độ chính xác: {exc}")

