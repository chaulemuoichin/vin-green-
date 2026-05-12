"""API-key auth on /forecast and /alerts.

When ``API_KEYS`` is unset the API is open (dev mode). When set, the
header ``X-API-Key`` must contain one of the listed keys.
"""

from __future__ import annotations

import importlib
from collections.abc import Iterator

import pytest

from hanoi_air.config import reload_settings

try:
    from fastapi.testclient import TestClient
except Exception:  # pragma: no cover - FastAPI absent
    TestClient = None  # type: ignore


def _fresh_app(monkeypatch: pytest.MonkeyPatch, **env: str):
    """Reload api.main with the given env applied so module-level state picks it up."""
    for key, value in env.items():
        monkeypatch.setenv(key, value)
    reload_settings()
    import api.main as api_main
    importlib.reload(api_main)
    return api_main.app


@pytest.fixture(autouse=True)
def _clear_settings_cache(monkeypatch: pytest.MonkeyPatch) -> Iterator[None]:
    """Each test starts with no API_KEYS in env unless it sets one."""
    monkeypatch.delenv("API_KEYS", raising=False)
    reload_settings()
    yield
    reload_settings()


def test_no_api_keys_means_open_access(monkeypatch: pytest.MonkeyPatch) -> None:
    if TestClient is None:
        pytest.skip("FastAPI test client not available")
    app = _fresh_app(monkeypatch)
    client = TestClient(app)
    response = client.get("/forecast?use_live=false&force_refresh=true&hour_offset=0")
    assert response.status_code == 200
    assert len(response.json()["forecasts"]) == 15


def test_missing_key_when_keys_configured_returns_401(monkeypatch: pytest.MonkeyPatch) -> None:
    if TestClient is None:
        pytest.skip("FastAPI test client not available")
    app = _fresh_app(monkeypatch, API_KEYS="demo,pitch")
    client = TestClient(app)
    response = client.get("/forecast?use_live=false&force_refresh=true&hour_offset=0")
    assert response.status_code == 401
    assert "API key" in response.json()["detail"]


def test_wrong_key_returns_401(monkeypatch: pytest.MonkeyPatch) -> None:
    if TestClient is None:
        pytest.skip("FastAPI test client not available")
    app = _fresh_app(monkeypatch, API_KEYS="demo,pitch")
    client = TestClient(app)
    response = client.get(
        "/forecast?use_live=false&force_refresh=true&hour_offset=0",
        headers={"X-API-Key": "wrong-key"},
    )
    assert response.status_code == 401


def test_correct_key_returns_200(monkeypatch: pytest.MonkeyPatch) -> None:
    if TestClient is None:
        pytest.skip("FastAPI test client not available")
    app = _fresh_app(monkeypatch, API_KEYS="demo,pitch")
    client = TestClient(app)
    response = client.get(
        "/forecast?use_live=false&force_refresh=true&hour_offset=0",
        headers={"X-API-Key": "demo"},
    )
    assert response.status_code == 200
    assert response.json()["district_count"] == 15


def test_health_is_always_open(monkeypatch: pytest.MonkeyPatch) -> None:
    if TestClient is None:
        pytest.skip("FastAPI test client not available")
    app = _fresh_app(monkeypatch, API_KEYS="demo,pitch")
    client = TestClient(app)
    assert client.get("/health").status_code == 200


def test_districts_is_always_open(monkeypatch: pytest.MonkeyPatch) -> None:
    if TestClient is None:
        pytest.skip("FastAPI test client not available")
    app = _fresh_app(monkeypatch, API_KEYS="demo,pitch")
    client = TestClient(app)
    response = client.get("/districts")
    assert response.status_code == 200
    assert len(response.json()["districts"]) == 15


def test_district_param_filters_rows(monkeypatch: pytest.MonkeyPatch) -> None:
    if TestClient is None:
        pytest.skip("FastAPI test client not available")
    app = _fresh_app(monkeypatch)
    client = TestClient(app)
    response = client.get("/forecast?district=hoan_kiem&use_live=false&force_refresh=true&hours=6")
    assert response.status_code == 200
    rows = response.json()["forecasts"]
    assert len(rows) == 6
    assert all(row["district_id"] == "hoan_kiem" for row in rows)


def test_fields_filter_trims_row_shape(monkeypatch: pytest.MonkeyPatch) -> None:
    if TestClient is None:
        pytest.skip("FastAPI test client not available")
    app = _fresh_app(monkeypatch)
    client = TestClient(app)
    response = client.get(
        "/forecast?district=hoan_kiem&hours=1&use_live=false&force_refresh=true"
        "&fields=vn_aqi,actions"
    )
    assert response.status_code == 200
    rows = response.json()["forecasts"]
    assert len(rows) == 1
    row = rows[0]
    # Allowlisted fields are present
    assert "vn_aqi" in row
    assert "actions" in row
    # Heavy field not in allowlist is gone
    assert "source_breakdown" not in row
    # Minimal-always fields remain
    assert {"district_id", "aqi", "pm25"} <= set(row)
