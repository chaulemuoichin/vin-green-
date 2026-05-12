"""JWT bearer auth on top of X-API-Key."""

from __future__ import annotations

import importlib
from collections.abc import Iterator

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


@pytest.fixture(autouse=True)
def _clear_settings(monkeypatch: pytest.MonkeyPatch) -> Iterator[None]:
    monkeypatch.delenv("API_KEYS", raising=False)
    monkeypatch.delenv("JWT_SECRET", raising=False)
    reload_settings()
    yield
    reload_settings()


def test_auth_token_returns_503_without_jwt_secret(monkeypatch: pytest.MonkeyPatch) -> None:
    if TestClient is None:
        pytest.skip("FastAPI test client not available")
    app = _fresh_app(monkeypatch, API_KEYS="demo")
    client = TestClient(app)
    response = client.post("/auth/token", headers={"X-API-Key": "demo"})
    assert response.status_code == 503
    assert "JWT" in response.json()["detail"]


def test_auth_token_requires_api_key(monkeypatch: pytest.MonkeyPatch) -> None:
    if TestClient is None:
        pytest.skip("FastAPI test client not available")
    app = _fresh_app(
        monkeypatch, API_KEYS="demo", JWT_SECRET="s" * 48,
    )
    client = TestClient(app)
    # No header → 401
    assert client.post("/auth/token").status_code == 401
    # Wrong key → 401
    assert client.post("/auth/token", headers={"X-API-Key": "wrong"}).status_code == 401


def test_auth_token_issues_jwt_for_valid_key(monkeypatch: pytest.MonkeyPatch) -> None:
    if TestClient is None:
        pytest.skip("FastAPI test client not available")
    app = _fresh_app(
        monkeypatch, API_KEYS="demo", JWT_SECRET="s" * 48,
    )
    client = TestClient(app)
    response = client.post("/auth/token", headers={"X-API-Key": "demo"})
    assert response.status_code == 200
    body = response.json()
    assert body["token_type"] == "bearer"
    assert body["access_token"].count(".") == 2  # JWT has 3 segments
    assert body["expires_in"] == 60 * 60


def test_bearer_jwt_authenticates_forecast(monkeypatch: pytest.MonkeyPatch) -> None:
    if TestClient is None:
        pytest.skip("FastAPI test client not available")
    app = _fresh_app(
        monkeypatch, API_KEYS="demo", JWT_SECRET="s" * 48,
    )
    client = TestClient(app)
    token = client.post("/auth/token", headers={"X-API-Key": "demo"}).json()["access_token"]
    # Use the JWT — no X-API-Key
    response = client.get(
        "/forecast?district=hoan_kiem&hours=1&use_live=false&force_refresh=true",
        headers={"Authorization": f"Bearer {token}"},
    )
    assert response.status_code == 200
    assert len(response.json()["forecasts"]) == 1


def test_invalid_bearer_is_rejected_with_401(monkeypatch: pytest.MonkeyPatch) -> None:
    if TestClient is None:
        pytest.skip("FastAPI test client not available")
    app = _fresh_app(
        monkeypatch, API_KEYS="demo", JWT_SECRET="s" * 48,
    )
    client = TestClient(app)
    response = client.get(
        "/forecast?use_live=false&hour_offset=0",
        headers={"Authorization": "Bearer not-a-real-token"},
    )
    assert response.status_code == 401
    assert "JWT" in response.json()["detail"]


def test_expired_bearer_returns_401_with_clear_message(monkeypatch: pytest.MonkeyPatch) -> None:
    if TestClient is None:
        pytest.skip("FastAPI test client not available")
    import datetime as _dt
    import jwt as _jwt

    app = _fresh_app(
        monkeypatch, API_KEYS="demo", JWT_SECRET="s" * 48,
    )
    client = TestClient(app)
    expired = _jwt.encode(
        {
            "sub": "demo",
            "iat": int((_dt.datetime.now(_dt.timezone.utc) - _dt.timedelta(hours=2)).timestamp()),
            "exp": int((_dt.datetime.now(_dt.timezone.utc) - _dt.timedelta(hours=1)).timestamp()),
            "iss": "hanoi-air-forecast",
        },
        "s" * 48,
        algorithm="HS256",
    )
    response = client.get(
        "/forecast?use_live=false&hour_offset=0",
        headers={"Authorization": f"Bearer {expired}"},
    )
    assert response.status_code == 401
    assert "expired" in response.json()["detail"].lower()


def test_api_key_path_still_works_when_jwt_configured(monkeypatch: pytest.MonkeyPatch) -> None:
    """Backwards compat: API-key clients keep working after JWT is enabled."""
    if TestClient is None:
        pytest.skip("FastAPI test client not available")
    app = _fresh_app(
        monkeypatch, API_KEYS="demo", JWT_SECRET="s" * 48,
    )
    client = TestClient(app)
    response = client.get(
        "/forecast?district=hoan_kiem&hours=1&use_live=false&force_refresh=true",
        headers={"X-API-Key": "demo"},
    )
    assert response.status_code == 200


def test_neither_credential_returns_401(monkeypatch: pytest.MonkeyPatch) -> None:
    if TestClient is None:
        pytest.skip("FastAPI test client not available")
    app = _fresh_app(
        monkeypatch, API_KEYS="demo", JWT_SECRET="s" * 48,
    )
    client = TestClient(app)
    response = client.get("/forecast?use_live=false&hour_offset=0")
    assert response.status_code == 401
    assert "Missing API key" in response.json()["detail"]
