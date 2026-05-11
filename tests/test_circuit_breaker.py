"""Circuit breaker tests for hanoi_air.retry.guard_source.

Verifies:
1. Repeated failures open the breaker after N attempts.
2. While open, the wrapped function is not called.
3. Successful call after cooldown resets the breaker.
"""

from __future__ import annotations

import time
from pathlib import Path

import pytest

from hanoi_air.config import Settings
from hanoi_air.retry import guard_source, is_circuit_open
from hanoi_air.sources import load_source_status


@pytest.fixture
def isolated_settings(tmp_path: Path) -> Settings:
    s = Settings(redis_url=None)
    object.__setattr__(s, "cache_file", tmp_path / "cache.json")
    object.__setattr__(s, "source_status_file", tmp_path / "status.json")
    return s


def test_breaker_opens_after_threshold(isolated_settings: Settings) -> None:
    calls = {"n": 0}

    @guard_source("aqicn", threshold=3, cooldown_minutes=5, fallback=[])
    def flaky(settings: Settings | None = None) -> list:
        calls["n"] += 1
        raise RuntimeError("simulated 500")

    # 3 failures should open the breaker
    for _ in range(3):
        result = flaky(isolated_settings)
        assert result == []
    assert calls["n"] == 3
    assert is_circuit_open("aqicn", isolated_settings)

    # 4th call: breaker open, function NOT called
    flaky(isolated_settings)
    assert calls["n"] == 3, "function should not be called while breaker is open"


def test_breaker_closes_on_success(isolated_settings: Settings) -> None:
    state = {"fail": True}

    @guard_source("openaq", threshold=2, cooldown_minutes=5, fallback=[])
    def maybe(settings: Settings | None = None) -> list:
        if state["fail"]:
            raise RuntimeError("down")
        return ["ok"]

    # Trip the breaker
    maybe(isolated_settings)
    maybe(isolated_settings)
    assert is_circuit_open("openaq", isolated_settings)

    # Manually clear `circuit_open_until` to simulate cooldown elapsed,
    # then a success closes it.
    from hanoi_air.sources import save_source_status

    status = load_source_status(isolated_settings)
    status["openaq"]["circuit_open_until"] = time.time() - 1
    save_source_status(status, isolated_settings)
    assert not is_circuit_open("openaq", isolated_settings)

    state["fail"] = False
    result = maybe(isolated_settings)
    assert result == ["ok"]

    # consecutive_failures reset
    final = load_source_status(isolated_settings).get("openaq", {})
    assert final["consecutive_failures"] == 0
    assert not final.get("circuit_open_until")
