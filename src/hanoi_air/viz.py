from __future__ import annotations

import math

from .geography import district_features, load_districts
from .interpolation import idw_interpolate
from .weather import offset_latlon, wind_to_unit

_HANOI_URBAN_BOUNDS = {
    "lat_min": 20.88,
    "lat_max": 21.13,
    "lon_min": 105.72,
    "lon_max": 105.97,
}


def aqi_color(aqi: int) -> str:
    if aqi <= 50:
        return "#2ecc71"
    if aqi <= 100:
        return "#f1c40f"
    if aqi <= 150:
        return "#e67e22"
    if aqi <= 200:
        return "#e74c3c"
    if aqi <= 300:
        return "#8e44ad"
    return "#7f1d1d"


def pm25_color(pm25: float) -> str:
    if pm25 <= 12:
        return "#2ecc71"
    if pm25 <= 35.4:
        return "#f1c40f"
    if pm25 <= 55.4:
        return "#e67e22"
    if pm25 <= 150.4:
        return "#e74c3c"
    return "#8e44ad"


def _wind_arrow_marker(lat: float, lon: float, wind_dir_deg: float, speed_mps: float):
    """Create a rotated CSS-triangle arrow pointing downwind."""
    try:
        import folium  # type: ignore
    except Exception:
        return None
    downwind = (wind_dir_deg + 180.0) % 360.0
    opacity = min(1.0, 0.4 + speed_mps * 0.08)
    scale = min(1.6, 0.8 + speed_mps * 0.12)
    html = (
        f'<div style="'
        f"width:0;height:0;"
        f"border-left:{int(5*scale)}px solid transparent;"
        f"border-right:{int(5*scale)}px solid transparent;"
        f"border-bottom:{int(18*scale)}px solid #93c5fd;"
        f"opacity:{opacity:.2f};"
        f"transform:rotate({downwind:.1f}deg);"
        f"transform-origin:50% 100%;"
        f'"></div>'
    )
    w = int(10 * scale)
    h = int(18 * scale)
    return folium.Marker(
        location=[lat, lon],
        icon=folium.DivIcon(html=html, icon_size=(w, h), icon_anchor=(w // 2, h // 2)),
        tooltip=f"Gió {wind_dir_deg:.0f}° — {speed_mps:.1f} m/s",
    )


def _interpolated_heatmap_points(
    row_by_id: dict,
    districts: list,
    grid_size: int = 22,
    pollutant: str = "pm25",
) -> list[list]:
    """IDW-interpolate district values onto a grid for a smooth heatmap."""
    station_points = []
    for district in districts:
        row = row_by_id.get(district.district_id)
        if not row:
            continue
        value = float(row.get(pollutant) or row.get("pm25") or 0)
        if value > 0:
            station_points.append({"lat": district.lat, "lon": district.lon, "value": value})
    if not station_points:
        return []
    b = _HANOI_URBAN_BOUNDS
    grid_targets = [
        {
            "lat": b["lat_min"] + (b["lat_max"] - b["lat_min"]) * i / (grid_size - 1),
            "lon": b["lon_min"] + (b["lon_max"] - b["lon_min"]) * j / (grid_size - 1),
        }
        for i in range(grid_size)
        for j in range(grid_size)
    ]
    values = idw_interpolate(station_points, grid_targets, power=2.0, max_distance_km=60.0)
    valid = [v for v in values if math.isfinite(v) and v > 0]
    cap = max(valid) if valid else 100.0
    heat_points = []
    for target, value in zip(grid_targets, values, strict=True):
        if math.isfinite(value) and value > 0:
            heat_points.append([target["lat"], target["lon"], min(1.0, value / cap)])
    return heat_points


def _downwind_color_for_score(score: float) -> str:
    """Pick a wedge fill color from a plasma-ish ramp."""
    if score >= 0.55:
        return "#ef4444"  # high
    if score >= 0.30:
        return "#f97316"  # medium
    if score >= 0.10:
        return "#eab308"  # low
    return "#a78bfa"  # marginal


def build_folium_map(
    bundle: dict,
    hour_offset: int = 0,
    selected_district: str | None = None,
    show_downwind: bool = True,
):
    try:
        import folium  # type: ignore
        from folium.plugins import HeatMap  # type: ignore
    except Exception:
        return None

    districts = load_districts()
    by_id = {district.district_id: district for district in districts}
    hour_rows = [
        row for row in bundle.get("forecasts", []) if int(row["hour_offset"]) == hour_offset
    ]
    if not hour_rows:
        hour_rows = bundle.get("forecasts", [])[: len(districts)]
    row_by_id = {row["district_id"]: row for row in hour_rows}

    center = [21.018, 105.828]
    fmap = folium.Map(
        location=center,
        zoom_start=13,
        tiles="https://{s}.basemaps.cartocdn.com/dark_all/{z}/{x}/{y}{r}.png",
        attr='&copy; <a href="https://carto.com/attributions">CARTO</a>',
        control_scale=True,
    )

    # ── Layer 1: District polygons (AQI fill) ─────────────────────────────
    def style_function(feature):  # type: ignore[no-untyped-def]
        district_id = feature["properties"]["district_id"]
        row = row_by_id.get(district_id)
        color = aqi_color(int(row["aqi"])) if row else "#95a5a6"
        weight = 3 if selected_district == district_id else 1
        fill_opacity = 0.42 if selected_district == district_id else 0.22
        return {"fillColor": color, "color": color, "weight": weight, "fillOpacity": fill_opacity}

    district_layer = folium.FeatureGroup(name="Quận — màu AQI", show=False)
    folium.GeoJson(
        district_features(districts),
        style_function=style_function,
        tooltip=folium.GeoJsonTooltip(fields=["name"], aliases=["Quận:"]),
    ).add_to(district_layer)
    district_layer.add_to(fmap)

    # ── Layer 2: PM2.5 heatmap (interpolated IDW grid) ────────────────────
    heatmap_layer = folium.FeatureGroup(name="Heatmap PM2.5", show=True)
    heat_points = _interpolated_heatmap_points(row_by_id, districts, pollutant="pm25")
    if heat_points:
        HeatMap(
            heat_points,
            min_opacity=0.25,
            radius=14,
            blur=18,
            max_zoom=14,
            gradient={
                0.0: "#2ecc71",
                0.35: "#f1c40f",
                0.6: "#e67e22",
                0.8: "#e74c3c",
                1.0: "#8e44ad",
            },
        ).add_to(heatmap_layer)
    heatmap_layer.add_to(fmap)

    # ── Layer 3: Wind arrows (per district, sized by speed) ───────────────
    wind_layer = folium.FeatureGroup(name="Hướng gió", show=True)
    unique_winds: dict = {}
    for row in hour_rows:
        district = by_id.get(row["district_id"])
        if not district:
            continue
        key = (round(float(row["wind_dir_deg"]), 0), round(float(row["wind_speed_mps"]), 1))
        if key in unique_winds:
            continue
        unique_winds[key] = True
        arrow = _wind_arrow_marker(
            district.lat,
            district.lon,
            float(row["wind_dir_deg"]),
            float(row["wind_speed_mps"]),
        )
        if arrow:
            arrow.add_to(wind_layer)
        east, north = wind_to_unit(float(row["wind_dir_deg"]))
        length_m = 2800 + float(row["wind_speed_mps"]) * 400
        end_lat, end_lon = offset_latlon(
            district.lat, district.lon, east * length_m, north * length_m
        )
        folium.PolyLine(
            locations=[[district.lat, district.lon], [end_lat, end_lon]],
            color="#93c5fd",
            weight=1.5,
            opacity=0.5,
            dash_array="4 4",
        ).add_to(wind_layer)
    wind_layer.add_to(fmap)

    # ── Layer 4: Station markers (AQI bubble + popup) ─────────────────────
    station_layer = folium.FeatureGroup(name="Trạm đo / quận", show=True)
    for row in hour_rows:
        district = by_id.get(row["district_id"])
        if not district:
            continue
        aqi = int(row["aqi"])
        radius = 11 if selected_district == district.district_id else 7
        folium.CircleMarker(
            location=[district.lat, district.lon],
            radius=radius,
            color=aqi_color(aqi),
            fill=True,
            fill_color=aqi_color(aqi),
            fill_opacity=0.88,
            popup=folium.Popup(
                (
                    f"<b>{district.name}</b><br>"
                    f"AQI <b>{aqi}</b> — {row['category']}<br>"
                    f"PM2.5 {row['pm25']} µg/m³ | NO2 {row['no2']} µg/m³<br>"
                    f"Gió {row['wind_speed_mps']} m/s<br>"
                    f"<i>{row['health_text']}</i>"
                ),
                max_width=340,
            ),
            tooltip=f"{district.name} — AQI {aqi}",
        ).add_to(station_layer)
    station_layer.add_to(fmap)

    # ── Layer 5: Emission sources ─────────────────────────────────────────
    source_layer = folium.FeatureGroup(name="Nguồn phát thải", show=False)
    for source in bundle.get("sources", []):
        folium.Marker(
            location=[source["lat"], source["lon"]],
            tooltip=source["name"],
            popup=f"{source['name']}<br>PM2.5 {source['pm25_g_s']} g/s | NO2 {source['no2_g_s']} g/s",
            icon=folium.Icon(color="darkred", icon="industry", prefix="fa"),
        ).add_to(source_layer)
    source_layer.add_to(fmap)

    # ── Layer 6: Downwind wedges (per source, fill by max score) ──────────
    if show_downwind:
        zones_by_hour = bundle.get("downwind_zones") or {}
        hour_zones = zones_by_hour.get(str(hour_offset)) or zones_by_hour.get(hour_offset) or []
        downwind_layer = folium.FeatureGroup(name="Vùng xuôi gió", show=True)
        for zone in hour_zones:
            polygon = zone.get("polygon") or []
            if len(polygon) < 3:
                continue
            score = float(zone.get("max_score", 0.0))
            color = _downwind_color_for_score(score)
            opacity = max(0.18, min(0.45, 0.15 + score * 0.45))
            affected_names = [d["district_name"] for d in zone.get("affected_districts", [])][:4]
            popup_html = (
                f"<b>{zone['source_name']}</b><br>"
                f"Gió {zone.get('wind_dir_deg', '-')}° · "
                f"{zone.get('wind_speed_mps', '-')} m/s<br>"
                f"Vùng ảnh hưởng: <b>{', '.join(affected_names) or '—'}</b><br>"
                f"Điểm cao nhất: <b>{score:.2f}</b>"
            )
            folium.Polygon(
                locations=polygon,
                color=color,
                weight=1.5,
                fill=True,
                fill_color=color,
                fill_opacity=opacity,
                popup=folium.Popup(popup_html, max_width=320),
                tooltip=f"Xuôi gió từ {zone['source_name']}",
            ).add_to(downwind_layer)
        downwind_layer.add_to(fmap)

    folium.LayerControl(collapsed=False).add_to(fmap)
    return fmap
