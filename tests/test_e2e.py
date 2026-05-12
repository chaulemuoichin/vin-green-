"""End-to-end smoke tests against a running stack.

These are skipped unless the ``E2E`` environment variable is truthy, so
they do not run as part of the default ``pytest`` invocation. To run:

    make prod-up
    E2E=1 API_BASE=http://localhost:8000 python -m pytest tests/test_e2e.py

If ``API_BASE`` points at nginx (``http://localhost``), the test prepends
``/api`` automatically for upstream routes.
"""

from __future__ import annotations

import os

import pytest

try:
    import httpx
except Exception:  # pragma: no cover
    httpx = None  # type: ignore


E2E_ENABLED = os.environ.get("E2E", "").lower() in ("1", "true", "yes")
API_BASE = os.environ.get("API_BASE", "http://localhost:8000").rstrip("/")
API_KEY = os.environ.get("E2E_API_KEY")  # set if API_KEYS configured upstream
TIMEOUT = float(os.environ.get("E2E_TIMEOUT", "10"))

# When hitting nginx, /forecast lives under /api/. Detect that and prefix.
USES_PROXY = API_BASE.endswith(":80") or API_BASE.endswith("localhost") or "/api" in API_BASE
ROUTE_PREFIX = "/api" if (USES_PROXY and "/api" not in API_BASE) else ""

pytestmark = pytest.mark.skipif(
    not E2E_ENABLED,
    reason="E2E tests disabled — set E2E=1 to run against a live stack",
)


def _headers() -> dict[str, str]:
    return {"X-API-Key": API_KEY} if API_KEY else {}


def _get(path: str) -> "httpx.Response":
    assert httpx is not None, "httpx required for E2E"
    return httpx.get(f"{API_BASE}{ROUTE_PREFIX}{path}", headers=_headers(), timeout=TIMEOUT)


def test_health_returns_ok() -> None:
    response = _get("/health")
    assert response.status_code == 200, response.text
    body = response.json()
    assert body["status"] == "ok"


def test_districts_returns_fifteen() -> None:
    response = _get("/districts")
    assert response.status_code == 200
    payload = response.json()
    assert len(payload["districts"]) == 15
    ids = {d["district_id"] for d in payload["districts"]}
    # Spot-check canonical urban + peri-urban representatives
    assert {"hoan_kiem", "thach_that", "son_tay"} <= ids


def test_forecast_for_district_carries_full_shape() -> None:
    response = _get("/forecast?district=hoan_kiem&hours=24")
    assert response.status_code == 200, response.text
    body = response.json()
    rows = body["forecasts"]
    assert len(rows) == 24
    row = rows[0]
    expected = {"pm25", "no2", "aqi", "category", "vn_aqi",
                "vn_category", "source_breakdown", "downwind_risk", "actions"}
    missing = expected - set(row)
    assert not missing, f"Missing fields on /forecast row: {missing}"
    # source_breakdown must be a normalised pie
    shares = row["source_breakdown"]
    assert abs(sum(shares.values()) - 1.0) < 1e-2


def test_forecast_fields_allowlist_trims_payload() -> None:
    response = _get(
        "/forecast?district=hoan_kiem&hours=1&fields=vn_aqi,actions"
    )
    assert response.status_code == 200
    row = response.json()["forecasts"][0]
    assert "vn_aqi" in row
    assert "actions" in row
    assert "source_breakdown" not in row


def test_alerts_responds() -> None:
    response = _get("/alerts")
    assert response.status_code == 200
    body = response.json()
    assert "alerts" in body
    assert "generated_at" in body
