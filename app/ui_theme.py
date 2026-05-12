from __future__ import annotations

AQI_STATES: tuple[dict[str, object], ...] = (
    {"max": 50, "label": "Tot", "color": "#2fdd8a", "text": "Tot"},
    {"max": 100, "label": "Trung binh", "color": "#e2c044", "text": "Trung binh"},
    {"max": 150, "label": "Khong tot", "color": "#f28c38", "text": "Khong tot"},
    {"max": 200, "label": "Xau", "color": "#ef5350", "text": "Xau"},
    {"max": 300, "label": "Rat xau", "color": "#b66cff", "text": "Rat xau"},
    {"max": 500, "label": "Nguy hai", "color": "#8b1e2d", "text": "Nguy hai"},
)

TEXT_COLORS = {
    "primary": "#eef2f6",
    "secondary": "#b6c2cf",
    "muted": "#8794a3",
    "faint": "#66717f",
}

SURFACE_COLORS = {
    "page": "#070907",
    "panel": "rgba(18, 22, 20, 0.86)",
    "panel_soft": "rgba(255, 255, 255, 0.045)",
    "border": "rgba(230, 238, 232, 0.105)",
    "border_strong": "rgba(230, 238, 232, 0.18)",
}

ACCENTS = {
    "pm25": "#f28c38",
    "no2": "#9ec5ff",
    "wind": "#62d6b1",
    "plume": "#b6c2cf",
    "info": "#a7c7b4",
    "danger": "#ef5350",
}

RADIUS = {
    "sm": "6px",
    "md": "8px",
    "lg": "10px",
}


def aqi_state(aqi: int) -> dict[str, object]:
    for state in AQI_STATES:
        if aqi <= int(state["max"]):
            return state
    return AQI_STATES[-1]


def global_css() -> str:
    return """
<style>
@import url('https://fonts.googleapis.com/css2?family=IBM+Plex+Sans:wght@400;500;600;700&family=IBM+Plex+Mono:wght@400;500;600&display=swap');

:root {
    --air-bg: #070907;
    --air-panel: rgba(18, 22, 20, 0.86);
    --air-panel-soft: rgba(255, 255, 255, 0.045);
    --air-border: rgba(230, 238, 232, 0.105);
    --air-border-strong: rgba(230, 238, 232, 0.18);
    --air-text: #eef2f6;
    --air-text-2: #b6c2cf;
    --air-muted: #8794a3;
    --air-faint: #66717f;
    --air-green: #62d6b1;
    --air-danger: #ef5350;
}

*, *::before, *::after { box-sizing: border-box; }

html, body, .stApp {
    font-family: 'IBM Plex Sans', 'Segoe UI', sans-serif !important;
    background:
        linear-gradient(180deg, rgba(20, 24, 20, 0.96), rgba(7, 9, 7, 1) 46%),
        radial-gradient(circle at 74% 8%, rgba(98, 214, 177, 0.08), transparent 32%);
    color: var(--air-text) !important;
}

#MainMenu, footer { visibility: hidden; }
.stDeployButton { display: none !important; }
.block-container { padding: 1rem 1.35rem 2rem !important; max-width: 100% !important; }

[data-testid="stSidebar"] {
    background: #0b0e0c !important;
    border-right: 1px solid var(--air-border) !important;
}
[data-testid="stSidebar"] > div { padding-top: 1rem; }
[data-testid="stSidebar"] label,
[data-testid="stSidebar"] .stSlider label,
[data-testid="stSidebar"] p {
    color: var(--air-text-2) !important;
    font-size: 0.78rem !important;
    text-transform: uppercase;
    letter-spacing: 0.06em;
}

.stButton > button {
    background: rgba(98, 214, 177, 0.08) !important;
    border: 1px solid rgba(98, 214, 177, 0.28) !important;
    color: #bff7e5 !important;
    border-radius: 8px !important;
    font-size: 0.86rem !important;
    font-weight: 600 !important;
    min-height: 2.25rem !important;
}
.stButton > button:hover {
    background: rgba(98, 214, 177, 0.15) !important;
    border-color: rgba(98, 214, 177, 0.55) !important;
}

[data-testid="stSelectbox"] > div > div {
    background: rgba(255,255,255,0.045) !important;
    border: 1px solid var(--air-border-strong) !important;
    border-radius: 8px !important;
    color: var(--air-text) !important;
}

[data-testid="stSlider"] [data-baseweb="slider"] div[role="slider"] {
    background: var(--air-green) !important;
    border-color: var(--air-green) !important;
}
[data-testid="stSlider"] [data-baseweb="slider"] > div > div > div {
    background: var(--air-green) !important;
}

[data-testid="stTabs"] [data-baseweb="tab-list"] {
    background: rgba(255,255,255,0.035) !important;
    border-radius: 8px !important;
    padding: 3px !important;
    border: 1px solid var(--air-border) !important;
}
[data-testid="stTabs"] [data-baseweb="tab"] {
    border-radius: 6px !important;
    color: var(--air-muted) !important;
    font-size: 0.86rem !important;
    font-weight: 600 !important;
    padding: 5px 18px !important;
}
[data-testid="stTabs"] [aria-selected="true"] {
    background: rgba(98, 214, 177, 0.12) !important;
    color: #c9f7e7 !important;
}

[data-testid="stDataFrame"] > div {
    background: rgba(255,255,255,0.025) !important;
    border: 1px solid var(--air-border) !important;
    border-radius: 8px !important;
}

hr { border-color: var(--air-border) !important; margin: 10px 0 !important; }
iframe { border-radius: 8px !important; border: 1px solid var(--air-border-strong) !important; }
.js-plotly-plot { border-radius: 8px !important; overflow: hidden; }

.air-title {
    margin: 0;
    color: var(--air-text);
    font-size: 1.28rem;
    line-height: 1.15;
    font-weight: 700;
}
.air-subtitle {
    color: var(--air-muted);
    font-size: 0.82rem;
    margin-top: 4px;
}
.air-section-label {
    color: var(--air-text-2);
    font-size: 0.75rem;
    text-transform: uppercase;
    letter-spacing: 0.075em;
    margin: 0 0 8px;
    font-weight: 700;
}
.air-card {
    background: var(--air-panel-soft);
    border: 1px solid var(--air-border);
    border-radius: 8px;
}

@media (max-width: 1100px) {
    .block-container { padding-left: .8rem !important; padding-right: .8rem !important; }
    .air-title { font-size: 1.08rem; }
}
</style>
"""
