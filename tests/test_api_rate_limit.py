"""slowapi rate-limit wiring on /forecast and /alerts."""

from __future__ import annotations

import importlib

import pytest

from hanoi_air.config import reload_settings

try:
    from fastapi.testclient import TestClient
except Exception:  # pragma: no cover
    TestClient = None  # type: ignore


def _fresh_app(monkeypatch: pytest.MonkeyPatch, **env: str):
    for key, value in env.items():
        monkeypatch.setenv(key, value)
    reload_settings()
    import api.main as api_main
    importlib.reload(api_main)
    return api_main.app


def test_rate_limit_kicks_in_at_configured_threshold(monkeypatch: pytest.MonkeyPatch) -> None:
    if TestClient is None:
        pytest.skip("FastAPI test client not available")
    monkeypatch.delenv("API_KEYS", raising=False)
    app = _fresh_app(monkeypatch, RATE_LIMIT_FORECAST="3/minute")
    client = TestClient(app)
    url = "/forecast?use_live=false&force_refresh=false&hour_offset=0"

    # First 3 requests within the window must succeed.
    for _ in range(3):
        assert client.get(url).status_code == 200
    # The 4th must be rejected.
    over = client.get(url)
    assert over.status_code == 429
    body = over.json()
    assert body["type"] == "rate_limit_exceeded"


def test_health_is_not_rate_limited(monkeypatch: pytest.MonkeyPatch) -> None:
    if TestClient is None:
        pytest.skip("FastAPI test client not available")
    monkeypatch.delenv("API_KEYS", raising=False)
    app = _fresh_app(monkeypatch, RATE_LIMIT_FORECAST="1/minute")
    client = TestClient(app)
    # Many /health hits in quick succession must all 200 — /health is exempt.
    for _ in range(8):
        assert client.get("/health").status_code == 200


def test_alerts_uses_its_own_limit(monkeypatch: pytest.MonkeyPatch) -> None:
    if TestClient is None:
        pytest.skip("FastAPI test client not available")
    monkeypatch.delenv("API_KEYS", raising=False)
    # Tighten /alerts but leave /forecast generous — only /alerts should reject.
    app = _fresh_app(
        monkeypatch,
        RATE_LIMIT_FORECAST="100/minute",
        RATE_LIMIT_ALERTS="2/minute",
    )
    client = TestClient(app)
    for _ in range(2):
        assert client.get("/alerts?use_live=false").status_code == 200
    assert client.get("/alerts?use_live=false").status_code == 429
    # /forecast still has headroom
    assert client.get("/forecast?use_live=false&hour_offset=0").status_code == 200
