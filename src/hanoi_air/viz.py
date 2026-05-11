from __future__ import annotations

import json
import math

from branca.element import MacroElement
from jinja2 import Template

from .geography import district_features, load_districts
from .interpolation import idw_interpolate
_NORTHERN_VIETNAM_BOUNDS = {
    # Northern Vietnam land border + ~100 km buffer in every direction
    "lat_min": 18.5,
    "lat_max": 24.5,
    "lon_min": 101.0,
    "lon_max": 109.0,
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


def _wind_arrow_marker(
    lat: float,
    lon: float,
    wind_dir_deg: float,
    speed_mps: float,
    base_scale: float = 1.0,
    color: str = "#4ade80",
):
    """SVG arrow marker pointing downwind, sized by speed."""
    try:
        import folium  # type: ignore
    except Exception:
        return None

    # Rotate the horizontal SVG arrow (→) to point downwind.
    # SVG → points east (90° compass). Rotating by (dir+90)%360 points it downwind.
    svg_rotation = (wind_dir_deg + 90.0) % 360.0
    opacity = min(0.92, 0.40 + speed_mps * 0.07)
    size = int(32 * base_scale)
    half = size // 2

    html = (
        f'<div style="width:{size}px;height:{size}px;'
        f"display:flex;align-items:center;justify-content:center;"
        f"transform:rotate({svg_rotation:.1f}deg);"
        f'opacity:{opacity:.2f}">'
        f'<svg width="{int(26*base_scale)}" height="{int(12*base_scale)}" '
        f'viewBox="0 0 26 12" xmlns="http://www.w3.org/2000/svg">'
        f'<line x1="1" y1="6" x2="17" y2="6" stroke="{color}" stroke-width="2.2"/>'
        f'<polygon points="16,2 25,6 16,10" fill="{color}"/>'
        f"</svg>"
        f"</div>"
    )
    return folium.Marker(
        location=[lat, lon],
        icon=folium.DivIcon(html=html, icon_size=(size, size), icon_anchor=(half, half)),
        tooltip=f"Gió {wind_dir_deg:.0f}° — {speed_mps:.1f} m/s",
    )


def _build_velocity_wind_data(wind_grid: list[dict], hour_offset: int) -> list[dict] | None:
    """Convert regional wind grid to leaflet-velocity U/V arrays (north-to-south scan)."""
    pts = [
        w for w in wind_grid
        if str(w.get("grid_level", "regional")) == "regional"
        and int(w["hour_offset"]) == hour_offset
    ]
    if len(pts) < 4:
        return None

    LATS = [19.8, 20.4, 21.0, 21.6, 22.2, 22.8]
    LONS = [103.0, 103.7, 104.4, 105.1, 105.8, 106.5, 107.2]
    ny, nx = len(LATS), len(LONS)

    lookup: dict[tuple[float, float], tuple[float, float]] = {}
    for pt in pts:
        key = (round(float(pt["lat"]), 1), round(float(pt["lon"]), 1))
        lookup[key] = (float(pt["wind_speed_mps"]), float(pt["wind_dir_deg"]))

    u_data: list[float] = []
    v_data: list[float] = []
    for lat in reversed(LATS):  # la1 > la2: north-to-south scan
        for lon in LONS:
            speed, direction = lookup.get((round(lat, 1), round(lon, 1)), (3.0, 0.0))
            dir_rad = math.radians(direction)
            u_data.append(round(-speed * math.sin(dir_rad), 3))
            v_data.append(round(-speed * math.cos(dir_rad), 3))

    header_base: dict = {
        "parameterUnit": "m.s-1",
        "lo1": LONS[0], "lo2": LONS[-1],
        "la1": LATS[-1], "la2": LATS[0],
        "dx": round(LONS[1] - LONS[0], 2),
        "dy": round(LATS[1] - LATS[0], 2),
        "nx": nx, "ny": ny,
        "numberPoints": nx * ny,
        "scanMode": 0,
        "refTime": "2024-01-01 00:00:00",
    }
    return [
        {"header": {**header_base, "parameterNumber": 2, "parameterNumberName": "u-component_of_wind"}, "data": u_data},
        {"header": {**header_base, "parameterNumber": 3, "parameterNumberName": "v-component_of_wind"}, "data": v_data},
    ]


class _PM25HeatmapLegend(MacroElement):
    """Floating PM2.5 colorbar legend (Leaflet control, bottom-right).

    Matches the absolute jet gradient used by the heatmap. Tick positions
    correspond to PM2.5 levels normalized against _PM25_HEATMAP_CAP (80 µg/m³):
    0, 5, 10, 15, 20, 50, 80 — same scale as the reference satellite image.
    """

    def __init__(self):
        super().__init__()
        self._template = Template(
            u"""
            {% macro script(this, kwargs) %}
            (function() {
                var map_ = {{ this._parent.get_name() }};
                var legend = L.control({position: 'bottomright'});
                legend.onAdd = function() {
                    var div = L.DomUtil.create('div', 'pm25-legend');
                    div.style.background = 'rgba(15,20,35,0.88)';
                    div.style.border = '1px solid rgba(255,255,255,0.15)';
                    div.style.borderRadius = '10px';
                    div.style.padding = '8px 14px 12px';
                    div.style.color = '#e2e8f0';
                    div.style.fontFamily = 'Inter, -apple-system, sans-serif';
                    div.style.fontSize = '11px';
                    div.style.boxShadow = '0 4px 20px rgba(0,0,0,0.4)';
                    div.innerHTML = [
                        '<div style="text-align:center;font-weight:600;margin-bottom:6px;letter-spacing:0.05em;color:#cbd5e1">PM2.5 [&mu;g/m&sup3;]</div>',
                        '<div style="position:relative;width:300px;height:30px">',
                          '<div style="position:absolute;top:0;left:0;right:0;height:13px;border-radius:3px;border:1px solid rgba(255,255,255,0.1);background:linear-gradient(to right,#000080 0%,#0040ff 12%,#00ffff 25%,#00ff00 38%,#ffff00 50%,#ff8000 63%,#ff2000 75%,#990000 88%,#4d0000 100%)"></div>',
                          '<span style="position:absolute;top:16px;left:0%;transform:translateX(-50%);color:#94a3b8;font-size:10px">40</span>',
                          '<span style="position:absolute;top:16px;left:25%;transform:translateX(-50%);color:#94a3b8;font-size:10px">50</span>',
                          '<span style="position:absolute;top:16px;left:50%;transform:translateX(-50%);color:#94a3b8;font-size:10px">60</span>',
                          '<span style="position:absolute;top:16px;left:75%;transform:translateX(-50%);color:#94a3b8;font-size:10px">70</span>',
                          '<span style="position:absolute;top:16px;left:100%;transform:translateX(-50%);color:#94a3b8;font-size:10px">80</span>',
                        '</div>'
                    ].join('');
                    L.DomEvent.disableClickPropagation(div);
                    L.DomEvent.disableScrollPropagation(div);
                    return div;
                };
                legend.addTo(map_);
            })();
            {% endmacro %}
            """
        )


class _ZoomAdaptiveWindLayer(MacroElement):
    """Swaps regional/medium/fine wind FeatureGroups based on zoom level.

    zoom < zoom_med  → regional (coarse, Northern Vietnam)
    zoom_med <= zoom < zoom_fine → medium (Hanoi+60km)
    zoom >= zoom_fine → fine (core Hanoi)
    """

    def __init__(
        self,
        regional_layer: object,
        medium_layer: object,
        fine_layer: object,
        zoom_med: int = 10,
        zoom_fine: int = 12,
    ):
        super().__init__()
        self.regional_name = regional_layer.get_name()  # type: ignore[attr-defined]
        self.medium_name = medium_layer.get_name()  # type: ignore[attr-defined]
        self.fine_name = fine_layer.get_name()  # type: ignore[attr-defined]
        self.zoom_med = zoom_med
        self.zoom_fine = zoom_fine
        self._template = Template(
            u"""
            {% macro script(this, kwargs) %}
            (function() {
                var map_ = {{ this._parent.get_name() }};
                var regionalLayer = {{ this.regional_name }};
                var mediumLayer = {{ this.medium_name }};
                var fineLayer = {{ this.fine_name }};
                var zoomMed = {{ this.zoom_med }};
                var zoomFine = {{ this.zoom_fine }};

                function updateWindLayers() {
                    var zoom = map_.getZoom();
                    if (map_.hasLayer(regionalLayer)) map_.removeLayer(regionalLayer);
                    if (map_.hasLayer(mediumLayer)) map_.removeLayer(mediumLayer);
                    if (map_.hasLayer(fineLayer)) map_.removeLayer(fineLayer);
                    if (zoom < zoomMed) {
                        regionalLayer.addTo(map_);
                    } else if (zoom < zoomFine) {
                        mediumLayer.addTo(map_);
                    } else {
                        fineLayer.addTo(map_);
                    }
                }
                map_.on('zoomend', updateWindLayers);
                setTimeout(updateWindLayers, 200);
            })();
            {% endmacro %}
            """
        )


class _VelocityWindLayer(MacroElement):
    """Animated wind particle layer via leaflet-velocity CDN plugin."""

    def __init__(self, wind_data: list[dict]):
        super().__init__()
        self.wind_json = json.dumps(wind_data, separators=(",", ":"))
        self._template = Template(
            u"""
            {% macro script(this, kwargs) %}
            (function() {
                var lnk = document.createElement('link');
                lnk.rel = 'stylesheet';
                lnk.href = 'https://cdn.jsdelivr.net/npm/leaflet-velocity@2.1.2/dist/leaflet-velocity.min.css';
                document.head.appendChild(lnk);

                var scr = document.createElement('script');
                scr.src = 'https://cdn.jsdelivr.net/npm/leaflet-velocity@2.1.2/dist/leaflet-velocity.min.js';
                scr.onload = function() {
                    try {
                        var map_ = {{ this._parent.get_name() }};
                        var windData = {{ this.wind_json }};
                        L.velocityLayer({
                            displayValues: true,
                            displayOptions: {
                                velocityType: "Gió",
                                position: "bottomleft",
                                emptyString: "Không có dữ liệu gió",
                                angleConvention: "bearingCCW",
                                speedUnit: "m/s"
                            },
                            data: windData,
                            maxVelocity: 15,
                            colorScale: ["#4ade80", "#86efac", "#a3e6b5", "#93c5fd", "#60a5fa"],
                            opacity: 0.72,
                            particleAge: 90,
                            lineWidth: 1.8,
                            particleMultiplier: 0.003
                        }).addTo(map_);
                    } catch(e) { console.warn('Wind layer init failed:', e); }
                };
                scr.onerror = function() { console.warn('leaflet-velocity CDN load failed'); };
                document.head.appendChild(scr);
            })();
            {% endmacro %}
            """
        )


_PM25_HEATMAP_MIN = 40.0  # µg/m³ — bottom of the jet scale
_PM25_HEATMAP_MAX = 80.0  # µg/m³ — top of the jet scale


def _interpolated_heatmap_points(
    row_by_id: dict,
    districts: list,
    regional_cities_hour: list[dict] | None = None,
    grid_size: int = 48,
    pollutant: str = "pm25",
) -> list[list]:
    """IDW-interpolate Hanoi districts + Northern Vietnam cities onto a regional grid.

    Output values are normalized to [0, 1] against a fixed PM2.5 range (40–80 µg/m³)
    so the colormap is stable across hours / data refreshes. Values below 40 clamp
    to deep blue; above 80 saturate at dark red.
    """
    station_points = []
    for district in districts:
        row = row_by_id.get(district.district_id)
        if not row:
            continue
        value = float(row.get(pollutant) or row.get("pm25") or 0)
        if value > 0:
            station_points.append({"lat": district.lat, "lon": district.lon, "value": value})
    for city in (regional_cities_hour or []):
        value = float(city.get(pollutant) or city.get("pm25") or 0)
        if value > 0:
            station_points.append(
                {"lat": float(city["lat"]), "lon": float(city["lon"]), "value": value}
            )
    if not station_points:
        return []
    b = _NORTHERN_VIETNAM_BOUNDS
    grid_targets = [
        {
            "lat": b["lat_min"] + (b["lat_max"] - b["lat_min"]) * i / (grid_size - 1),
            "lon": b["lon_min"] + (b["lon_max"] - b["lon_min"]) * j / (grid_size - 1),
        }
        for i in range(grid_size)
        for j in range(grid_size)
    ]
    values = idw_interpolate(station_points, grid_targets, power=2.2, max_distance_km=240.0)
    heat_points = []
    for target, value in zip(grid_targets, values, strict=True):
        if math.isfinite(value) and value > 0:
            normalized = (value - _PM25_HEATMAP_MIN) / (_PM25_HEATMAP_MAX - _PM25_HEATMAP_MIN)
            normalized = min(1.0, max(0.0, normalized))
            heat_points.append([target["lat"], target["lon"], normalized])
    return heat_points


def build_folium_map(bundle: dict, hour_offset: int = 0, selected_district: str | None = None):
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

    wind_grid: list[dict] = bundle.get("wind_grid", [])
    regional_cities: list[dict] = bundle.get("regional_cities", [])

    city_hour = [c for c in regional_cities if int(c["hour_offset"]) == hour_offset]

    # Zoom out to show northern Vietnam
    center = [21.3, 105.8]
    fmap = folium.Map(
        location=center,
        zoom_start=8,
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

    district_layer = folium.FeatureGroup(name="Quận Hà Nội — màu AQI", show=False)
    folium.GeoJson(
        district_features(districts),
        style_function=style_function,
        tooltip=folium.GeoJsonTooltip(fields=["name"], aliases=["Quận:"]),
    ).add_to(district_layer)
    district_layer.add_to(fmap)

    # ── Layer 2: PM2.5 heatmap (Northern Vietnam, jet scale, IDW grid) ────
    heatmap_layer = folium.FeatureGroup(name="Heatmap PM2.5 (Miền Bắc)", show=True)
    heat_points = _interpolated_heatmap_points(
        row_by_id, districts, regional_cities_hour=city_hour, pollutant="pm25"
    )
    if heat_points:
        # Absolute jet scale across 40..80 µg/m³ — each stop linearly mapped
        HeatMap(
            heat_points,
            min_opacity=0.55,
            radius=26,
            blur=22,
            max_zoom=14,
            gradient={
                0.00: "#000080",  # 40 µg/m³ — deep blue
                0.12: "#0040ff",  # 45     — blue
                0.25: "#00ffff",  # 50     — cyan
                0.38: "#00ff00",  # 55     — green
                0.50: "#ffff00",  # 60     — yellow
                0.63: "#ff8000",  # 65     — orange
                0.75: "#ff2000",  # 70     — red
                0.88: "#990000",  # 75     — dark red
                1.00: "#4d0000",  # 80+    — maroon
            },
        ).add_to(heatmap_layer)
    heatmap_layer.add_to(fmap)
    _PM25HeatmapLegend().add_to(fmap)

    # ── Layer 3: Regional cities AQI (outside Hanoi) ──────────────────────
    cities_layer = folium.FeatureGroup(name="AQI các tỉnh lân cận", show=True)
    for city in city_hour:
        aqi = int(city["aqi"])
        color = aqi_color(aqi)
        folium.CircleMarker(
            location=[city["lat"], city["lon"]],
            radius=9,
            color=color,
            fill=True,
            fill_color=color,
            fill_opacity=0.75,
            popup=folium.Popup(
                (
                    f"<b>{city['name']}</b><br>"
                    f"AQI <b>{aqi}</b> — {city['category']}<br>"
                    f"PM2.5 {city['pm25']} µg/m³ | NO₂ {city['no2']} µg/m³"
                ),
                max_width=260,
            ),
            tooltip=f"{city['name']} — AQI {aqi}",
        ).add_to(cities_layer)
        # City name label
        folium.Marker(
            location=[city["lat"] + 0.04, city["lon"]],
            icon=folium.DivIcon(
                html=(
                    f'<div style="font-size:9px;color:#cbd5e1;'
                    f'white-space:nowrap;font-weight:600;'
                    f'text-shadow:0 0 3px #000">{city["name"]}</div>'
                ),
                icon_size=(80, 14),
                icon_anchor=(40, 0),
            ),
        ).add_to(cities_layer)
    cities_layer.add_to(fmap)

    # ── Layer 4: Hanoi station markers (AQI bubble + popup) ───────────────
    station_layer = folium.FeatureGroup(name="Trạm Hà Nội", show=True)
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
    source_layer = folium.FeatureGroup(name="Nguồn phát thải", show=True)
    for source in bundle.get("sources", []):
        folium.Marker(
            location=[source["lat"], source["lon"]],
            tooltip=source["name"],
            popup=(
                f"{source['name']}<br>"
                f"PM2.5 {source['pm25_g_s']} g/s | NO2 {source['no2_g_s']} g/s"
            ),
            icon=folium.Icon(color="darkred", icon="industry", prefix="fa"),
        ).add_to(source_layer)
    source_layer.add_to(fmap)

    # ── Wind: 3-tier zoom-adaptive SVG arrow field ───────────────────────
    hour_wind = [w for w in wind_grid if int(w["hour_offset"]) == hour_offset]
    regional_pts = [w for w in hour_wind if str(w.get("grid_level", "regional")) == "regional"]
    medium_pts = [w for w in hour_wind if str(w.get("grid_level", "")) == "medium"]
    fine_pts = [w for w in hour_wind if str(w.get("grid_level", "")) == "fine"]

    wind_regional_layer = folium.FeatureGroup(name="Gió vùng (toàn miền Bắc)", show=True)
    if regional_pts:
        for pt in regional_pts:
            arrow = _wind_arrow_marker(
                pt["lat"], pt["lon"],
                pt["wind_dir_deg"], pt["wind_speed_mps"],
                base_scale=1.4, color="#4ade80",
            )
            if arrow:
                arrow.add_to(wind_regional_layer)
    elif hour_rows:
        sample = hour_rows[0]
        arrow = _wind_arrow_marker(
            21.03, 105.83,
            float(sample["wind_dir_deg"]), float(sample["wind_speed_mps"]),
            base_scale=1.4, color="#4ade80",
        )
        if arrow:
            arrow.add_to(wind_regional_layer)
    wind_regional_layer.add_to(fmap)

    wind_medium_layer = folium.FeatureGroup(name="Gió trung bình (Hà Nội+60km)", show=False)
    for pt in medium_pts:
        arrow = _wind_arrow_marker(
            pt["lat"], pt["lon"],
            pt["wind_dir_deg"], pt["wind_speed_mps"],
            base_scale=1.0, color="#93c5fd",
        )
        if arrow:
            arrow.add_to(wind_medium_layer)
    wind_medium_layer.add_to(fmap)

    wind_fine_layer = folium.FeatureGroup(name="Gió chi tiết (nội thành)", show=False)
    for pt in fine_pts:
        arrow = _wind_arrow_marker(
            pt["lat"], pt["lon"],
            pt["wind_dir_deg"], pt["wind_speed_mps"],
            base_scale=0.75, color="#7dd3fc",
        )
        if arrow:
            arrow.add_to(wind_fine_layer)
    wind_fine_layer.add_to(fmap)

    _ZoomAdaptiveWindLayer(
        wind_regional_layer, wind_medium_layer, wind_fine_layer,
        zoom_med=10, zoom_fine=12,
    ).add_to(fmap)

    # ── Wind: animated particle field (leaflet-velocity, optional) ───────
    velocity_data = _build_velocity_wind_data(wind_grid, hour_offset)
    if velocity_data:
        _VelocityWindLayer(velocity_data).add_to(fmap)

    folium.LayerControl(collapsed=False).add_to(fmap)
    return fmap
