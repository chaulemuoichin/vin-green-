from hanoi_air.config import get_settings
from hanoi_air.geography import load_districts
from hanoi_air.ingestion import (
    build_open_meteo_air_url,
    build_open_meteo_weather_url,
    build_overpass_roads_url,
    load_json,
    parse_open_meteo_air_payload,
    parse_open_meteo_weather_payload,
    parse_openaq_locations_payload,
    parse_overpass_roads_payload,
    parse_somo_html,
)
from hanoi_air.sources import SOURCE_REGISTRY


def test_source_registry_cadence_defaults():
    assert SOURCE_REGISTRY["open_meteo_weather"].cadence_minutes == 30
    assert SOURCE_REGISTRY["open_meteo_air"].quality_flag == "forecast_background"
    assert SOURCE_REGISTRY["openaq"].cadence_minutes == 60
    assert SOURCE_REGISTRY["overpass_roads"].cadence_minutes >= 43200


def test_open_meteo_weather_parser_and_url():
    settings = get_settings()
    payload = load_json(settings.sample_dir / "open_meteo_weather_sample.json")
    rows = parse_open_meteo_weather_payload(payload, horizon_hours=2)
    assert len(rows) == 2
    assert rows[0].wind_speed_mps == 2.4
    assert rows[0].precipitation_mm == 0.0
    url = build_open_meteo_weather_url(21.0278, 105.8342, horizon_hours=24)
    assert "api.open-meteo.com" in url
    assert "wind_speed_10m" in url


def test_open_meteo_air_parser_for_district_centroids():
    settings = get_settings()
    districts = load_districts()[:2]
    payload = load_json(settings.sample_dir / "open_meteo_air_sample.json")
    rows = parse_open_meteo_air_payload(payload, districts, horizon_hours=2)
    assert len(rows) == 4
    assert rows[0].district_id == districts[0].district_id
    assert rows[0].quality_flag == "forecast_background"
    districts = load_districts()
    url = build_open_meteo_air_url(districts, horizon_hours=24)
    assert "air-quality-api.open-meteo.com" in url
    assert url.count(",") >= len(districts) - 1


def test_openaq_and_somo_parsers():
    settings = get_settings()
    openaq_rows = parse_openaq_locations_payload(
        load_json(settings.sample_dir / "openaq_locations_sample.json")
    )
    assert {row.pollutant for row in openaq_rows} == {"pm25", "no2"}
    assert openaq_rows[0].quality_flag == "live_api"

    html = (settings.sample_dir / "somo_sample.html").read_text(encoding="utf-8")
    somo_rows = parse_somo_html(html, site_id="1")
    assert len(somo_rows) == 2
    assert somo_rows[0].quality_flag == "public_crawl"
    assert any(row.pollutant == "pm25" and row.concentration == 62.0 for row in somo_rows)


def test_overpass_static_proxy_parser_and_url():
    settings = get_settings()
    density = parse_overpass_roads_payload(
        load_json(settings.sample_dir / "overpass_roads_sample.json")
    )
    assert density
    assert max(density.values()) == 1.0
    assert "overpass-api.de" in build_overpass_roads_url()
