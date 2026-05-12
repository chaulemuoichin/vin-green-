"""Tests for FIRMS VIIRS fire detection parsing."""
from __future__ import annotations

from pathlib import Path

from hanoi_air.ingestion import parse_firms_viirs_csv


def _load_sample_csv() -> str:
    sample_path = Path(__file__).parents[1] / "data" / "sample" / "firms_viirs_sample.csv"
    return sample_path.read_text(encoding="utf-8")


class TestParseFirmsViirsCsv:
    def test_returns_fires_from_sample(self) -> None:
        fires = parse_firms_viirs_csv(_load_sample_csv())
        assert len(fires) >= 1

    def test_filters_low_confidence(self) -> None:
        fires = parse_firms_viirs_csv(_load_sample_csv())
        # The sample has 1 low-confidence row (confidence='l') — must be excluded
        assert all(f.confidence in ("n", "h") for f in fires)

    def test_filters_zero_frp(self) -> None:
        csv_with_zero = (
            "latitude,longitude,brightness,scan,track,acq_date,acq_time,"
            "satellite,instrument,confidence,version,bright_ti4,bright_ti5,frp,daynight\n"
            "20.5,103.5,300.0,0.4,0.4,2026-05-10,0542,N20,VIIRS,n,2.0NRT,300.0,280.0,0.0,D\n"
        )
        fires = parse_firms_viirs_csv(csv_with_zero)
        assert fires == []

    def test_distance_limit_600km(self) -> None:
        # Fire far from Hanoi (e.g., southern Vietnam ~1200 km away)
        csv_far = (
            "latitude,longitude,brightness,scan,track,acq_date,acq_time,"
            "satellite,instrument,confidence,version,bright_ti4,bright_ti5,frp,daynight\n"
            "10.0,106.0,300.0,0.4,0.4,2026-05-10,0542,N20,VIIRS,h,2.0NRT,300.0,280.0,80.0,D\n"
        )
        fires = parse_firms_viirs_csv(csv_far)
        assert fires == []

    def test_positive_frp_values(self) -> None:
        fires = parse_firms_viirs_csv(_load_sample_csv())
        assert all(f.frp > 0 for f in fires)

    def test_distance_within_600km(self) -> None:
        fires = parse_firms_viirs_csv(_load_sample_csv())
        assert all(f.distance_to_hanoi_km <= 600.0 for f in fires)

    def test_h3_index_assigned(self) -> None:
        fires = parse_firms_viirs_csv(_load_sample_csv())
        assert all(len(f.h3_index) == 15 for f in fires)

    def test_bearing_in_range(self) -> None:
        fires = parse_firms_viirs_csv(_load_sample_csv())
        assert all(0.0 <= f.bearing_from_hanoi_deg < 360.0 for f in fires)

    def test_timestamp_utc(self) -> None:
        from datetime import timezone
        fires = parse_firms_viirs_csv(_load_sample_csv())
        assert all(f.timestamp.tzinfo == timezone.utc for f in fires)

    def test_empty_csv_returns_empty_list(self) -> None:
        header_only = (
            "latitude,longitude,brightness,scan,track,acq_date,acq_time,"
            "satellite,instrument,confidence,version,bright_ti4,bright_ti5,frp,daynight\n"
        )
        fires = parse_firms_viirs_csv(header_only)
        assert fires == []

    def test_malformed_row_is_skipped(self) -> None:
        csv_with_bad_row = (
            "latitude,longitude,brightness,scan,track,acq_date,acq_time,"
            "satellite,instrument,confidence,version,bright_ti4,bright_ti5,frp,daynight\n"
            "not_a_number,103.5,300.0,0.4,0.4,2026-05-10,0542,N20,VIIRS,n,2.0NRT,300.0,280.0,65.0,D\n"
            "20.5,103.5,300.0,0.4,0.4,2026-05-10,0542,N20,VIIRS,h,2.0NRT,300.0,280.0,80.0,D\n"
        )
        fires = parse_firms_viirs_csv(csv_with_bad_row)
        # The bad row is skipped; the valid one is kept
        assert len(fires) == 1
