from hanoi_air.config import get_settings
from hanoi_air.ingestion import (
    load_air_readings,
    load_json,
    load_sources,
    parse_aqicn_payload,
    parse_openweather_air_payload,
)


def test_parse_aqicn_payload_sample():
    settings = get_settings()
    payload = load_json(settings.sample_dir / "aqicn_sample.json")
    readings = parse_aqicn_payload(payload)
    assert {reading.pollutant for reading in readings} == {"pm25", "no2"}
    assert readings[0].district == "Bắc Từ Liêm"
    assert readings[0].quality_flag == "live_api"


def test_parse_openweather_payload_sample():
    settings = get_settings()
    payload = load_json(settings.sample_dir / "openweather_air_sample.json")
    readings = parse_openweather_air_payload(payload)
    assert len(readings) == 2
    assert any(
        reading.pollutant == "pm25" and reading.concentration == 59.3 for reading in readings
    )


def test_sample_loaders_return_data_without_keys():
    readings = load_air_readings(get_settings(), use_live=False)
    sources = load_sources(get_settings())
    # 8 sample stations x 2 pollutants = 16 readings after district reduction (30 -> 12)
    assert len(readings) >= 14
    assert any(reading.quality_flag == "manual_validated" for reading in readings)
    assert any(source.source_id == "thach_ban_industrial" for source in sources)
