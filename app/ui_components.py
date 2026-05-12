from __future__ import annotations

from html import escape
from textwrap import dedent
from typing import Mapping

from ui_theme import ACCENTS, TEXT_COLORS, aqi_state


def _html(value: str) -> str:
    return " ".join(line.strip() for line in dedent(value).strip().splitlines())


def _pct(value: float, cap: float) -> int:
    return max(2, min(100, round(value / cap * 100)))


def section_label(text: str) -> str:
    return f'<div class="air-section-label">{escape(text)}</div>'


def source_badge(mode: str) -> str:
    labels = {
        "live": ("LIVE", "#2fdd8a", "Live sources active"),
        "free_api_background": ("BACKGROUND", "#e2c044", "Forecast background"),
        "sample": ("SAMPLE", "#8794a3", "Sample fallback"),
    }
    label, color, detail = labels.get(mode, (mode.upper(), "#8794a3", "Data mode"))
    return _html(f"""
    <span style="display:inline-flex;align-items:center;gap:8px;
        background:{color}18;border:1px solid {color}45;border-radius:999px;
        padding:5px 11px;color:{color};font-size:.73rem;font-weight:700;
        letter-spacing:.055em;white-space:nowrap">
        <span style="width:7px;height:7px;background:{color};border-radius:99px;
            box-shadow:0 0 12px {color}AA"></span>
        {escape(label)}
        <span style="color:{TEXT_COLORS['muted']};font-weight:500;letter-spacing:0">{escape(detail)}</span>
    </span>
    """)


def status_strip(generated_at: str, mode: str, source_count: int, source_note: str) -> str:
    timestamp = (generated_at or "").replace("T", " ")[:16] or "unknown"
    return _html(f"""
    <div style="display:flex;gap:8px;align-items:center;flex-wrap:wrap;margin-top:9px">
        {source_badge(mode)}
        <span style="color:{TEXT_COLORS['muted']};font-size:.78rem">
            Updated <span style="font-family:'IBM Plex Mono',monospace;color:{TEXT_COLORS['secondary']}">{escape(timestamp)} UTC</span>
        </span>
        <span style="color:{TEXT_COLORS['faint']};font-size:.78rem">|</span>
        <span style="color:{TEXT_COLORS['muted']};font-size:.78rem">{source_count} sources tracked</span>
        <span style="color:{TEXT_COLORS['faint']};font-size:.78rem">|</span>
        <span style="color:{TEXT_COLORS['secondary']};font-size:.78rem">{escape(source_note)}</span>
    </div>
    """)


def primary_aqi_summary(row: Mapping[str, object], selected_label: str) -> str:
    aqi = int(row["aqi"])
    state = aqi_state(aqi)
    color = str(state["color"])
    district = str(row["district_name"])
    title = selected_label if selected_label != "Toan Ha Noi" else district
    return _html(f"""
    <div style="background:linear-gradient(135deg,{color}20,rgba(255,255,255,.035));
        border:1px solid {color}55;border-radius:8px;padding:15px 16px;min-height:120px">
        <div style="color:{TEXT_COLORS['secondary']};font-size:.75rem;text-transform:uppercase;
            letter-spacing:.08em;font-weight:700">Primary readout</div>
        <div style="display:flex;align-items:flex-end;gap:14px;margin-top:8px">
            <div style="font-family:'IBM Plex Mono',monospace;font-size:3.2rem;line-height:.9;
                font-weight:700;color:{color}">{aqi}</div>
            <div style="padding-bottom:3px">
                <div style="color:{TEXT_COLORS['primary']};font-size:1.05rem;font-weight:700">{escape(title)}</div>
                <div style="color:{color};font-size:.9rem;font-weight:700;margin-top:2px">{escape(str(state['label']))}</div>
            </div>
        </div>
        <div style="display:flex;gap:8px;flex-wrap:wrap;margin-top:12px;color:{TEXT_COLORS['secondary']};font-size:.78rem">
            <span>PM2.5 <b style="color:{ACCENTS['pm25']}">{row['pm25']}</b> ug/m3</span>
            <span>NO2 <b style="color:{ACCENTS['no2']}">{row['no2']}</b> ug/m3</span>
            <span>Range <b>{row['uncertainty_low']}-{row['uncertainty_high']}</b> AQI</span>
        </div>
    </div>
    """)


def metric_card(label: str, value: str, unit: str = "", accent: str = "#b6c2cf") -> str:
    return _html(f"""
    <div style="background:rgba(255,255,255,.045);border:1px solid rgba(230,238,232,.105);
        border-radius:8px;padding:12px 13px;min-height:84px">
        <div style="color:{TEXT_COLORS['muted']};font-size:.72rem;text-transform:uppercase;
            letter-spacing:.065em;font-weight:700;white-space:normal">{escape(label)}</div>
        <div style="color:{accent};font-family:'IBM Plex Mono',monospace;font-size:1.42rem;
            font-weight:700;line-height:1.08;margin-top:6px;word-break:break-word">{escape(value)}</div>
        {f'<div style="color:{TEXT_COLORS["muted"]};font-size:.75rem;margin-top:2px">{escape(unit)}</div>' if unit else ''}
    </div>
    """)


def alert_banner(alerts: list[dict], fallback_row: Mapping[str, object]) -> str:
    if not alerts:
        return _html(f"""
        <div style="border:1px solid rgba(47,221,138,.28);background:rgba(47,221,138,.07);
            border-radius:8px;padding:10px 13px;color:#bff7d7;font-size:.86rem;margin-bottom:10px">
            No district has crossed the configured alert threshold for this forecast bundle.
        </div>
        """)
    first = alerts[0]
    district = str(first.get("district_name") or fallback_row.get("district_name") or "Unknown")
    value = first.get("value", fallback_row.get("aqi", ""))
    timestamp = str(first.get("timestamp") or "")[:16].replace("T", " ")
    return _html(f"""
    <div style="border:1px solid rgba(239,83,80,.46);background:linear-gradient(90deg,rgba(239,83,80,.16),rgba(239,83,80,.055));
        border-radius:8px;padding:11px 14px;color:#ffd2d0;font-size:.9rem;margin-bottom:10px">
        <b>{len(alerts)} alert districts</b>
        <span style="color:{TEXT_COLORS['secondary']}">| worst first:</span>
        <b>{escape(district)}</b>
        <span style="color:{TEXT_COLORS['secondary']}">value</span> <b>{escape(str(value))}</b>
        {f'<span style="color:{TEXT_COLORS["secondary"]}">at</span> <b>{escape(timestamp)}</b>' if timestamp else ''}
    </div>
    """)


def driver_breakdown(row: Mapping[str, object]) -> str:
    plume = float(row.get("plume_pm25") or 0)
    traffic = float(row.get("traffic_index") or 0)
    wind = float(row.get("wind_speed_mps") or 0)
    return _html(f"""
    <div style="background:rgba(255,255,255,.035);border:1px solid rgba(230,238,232,.105);
        border-radius:8px;padding:12px 13px;margin-top:9px">
        <div style="color:{TEXT_COLORS['secondary']};font-size:.74rem;text-transform:uppercase;
            letter-spacing:.07em;font-weight:700;margin-bottom:9px">Driver breakdown</div>
        {driver_row("Plume PM2.5", plume, 90, ACCENTS["plume"], f"{plume:.1f} ug/m3")}
        {driver_row("Traffic", traffic, 1, ACCENTS["pm25"], f"{traffic:.2f} index")}
        {driver_row("Ventilation wind", wind, 8, ACCENTS["wind"], f"{wind:.1f} m/s")}
    </div>
    """)


def driver_row(label: str, value: float, cap: float, color: str, value_text: str) -> str:
    width = _pct(value, cap)
    return _html(f"""
    <div style="margin-bottom:9px">
        <div style="display:flex;justify-content:space-between;gap:8px;font-size:.78rem">
            <span style="color:{TEXT_COLORS['secondary']}">{escape(label)}</span>
            <span style="color:{TEXT_COLORS['primary']};font-family:'IBM Plex Mono',monospace">{escape(value_text)}</span>
        </div>
        <div style="height:5px;background:rgba(255,255,255,.07);border-radius:99px;margin-top:5px">
            <div style="height:100%;width:{width}%;background:{color};border-radius:99px"></div>
        </div>
    </div>
    """)


def recommendation_card(text: str) -> str:
    return _html(f"""
    <div style="background:rgba(255,255,255,.035);border:1px solid rgba(230,238,232,.105);
        border-radius:8px;padding:11px 13px;font-size:.86rem;line-height:1.5;
        color:{TEXT_COLORS['secondary']};margin-top:9px">
        {escape(text)}
    </div>
    """)


def top5_row(rank: int, name: str, aqi: int) -> str:
    state = aqi_state(aqi)
    color = str(state["color"])
    bar = _pct(aqi, 300)
    return _html(f"""
    <div style="margin-bottom:10px">
        <div style="display:flex;justify-content:space-between;align-items:center;gap:10px;margin-bottom:4px">
            <span style="color:{TEXT_COLORS['secondary']};font-size:.82rem;min-width:0">
                <span style="color:{color};font-weight:700;margin-right:7px">#{rank}</span>{escape(name)}
            </span>
            <span style="color:{color};font-family:'IBM Plex Mono',monospace;font-weight:700;font-size:.86rem">{aqi}</span>
        </div>
        <div style="height:4px;background:rgba(255,255,255,.07);border-radius:99px">
            <div style="height:100%;width:{bar}%;background:{color};border-radius:99px"></div>
        </div>
    </div>
    """)


def map_header(hour: int, selected_label: str, has_wind: bool, has_regional: bool) -> str:
    layers = ["AQI districts", "PM2.5 heatmap"]
    if has_wind:
        layers.append("wind")
    if has_regional:
        layers.append("regional cities")
    return _html(f"""
    <div style="display:flex;justify-content:space-between;gap:12px;align-items:center;
        background:rgba(255,255,255,.035);border:1px solid rgba(230,238,232,.105);
        border-radius:8px;padding:9px 12px;margin-bottom:8px;flex-wrap:wrap">
        <div style="color:{TEXT_COLORS['primary']};font-weight:700;font-size:.9rem">
            Map state: <span style="font-family:'IBM Plex Mono',monospace;color:{ACCENTS['wind']}">T+{hour}h</span>
            <span style="color:{TEXT_COLORS['muted']};font-weight:500">/ {escape(selected_label)}</span>
        </div>
        <div style="color:{TEXT_COLORS['muted']};font-size:.78rem">{escape(' | '.join(layers))}</div>
    </div>
    """)


def aqi_legend() -> str:
    items = []
    for state in [
        (50, "Tot"),
        (100, "TB"),
        (150, "Khong tot"),
        (200, "Xau"),
        (300, "Rat xau"),
    ]:
        color = str(aqi_state(state[0])["color"])
        items.append(f'<span style="color:{color};white-space:nowrap">● {escape(state[1])} <= {state[0]}</span>')
    return _html(f"""
    <div style="display:flex;gap:10px;flex-wrap:wrap;margin-top:8px;padding:8px 11px;
        background:rgba(255,255,255,.035);border-radius:8px;border:1px solid rgba(230,238,232,.105);
        font-size:.74rem">
        <span style="color:{TEXT_COLORS['secondary']};font-weight:700;margin-right:3px">AQI colour</span>
        {''.join(items)}
        <span style="color:{TEXT_COLORS['faint']}">PM2.5 heatmap uses its own ug/m3 scale on the map.</span>
    </div>
    """)
