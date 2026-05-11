"""Cache concurrency tests — ensure parallel writes do not lose sibling keys.

This protects against the pre-Phase-1 bug where two workers writing different
keys concurrently could overwrite each other because reads were not under a
lock.
"""

from __future__ import annotations

import json
import multiprocessing as mp
from pathlib import Path

from hanoi_air.cache import load_cache, save_cache
from hanoi_air.config import Settings


def _build_settings(tmp_path: Path) -> Settings:
    """Settings that point cache at an isolated tmp dir."""
    s = Settings(redis_url=None)
    # Settings is pydantic BaseSettings (frozen via no Config.frozen, mutable here).
    object.__setattr__(s, "cache_file", tmp_path / "cache.json")
    object.__setattr__(s, "source_status_file", tmp_path / "status.json")
    return s


def _writer(args: tuple) -> None:
    """Worker entrypoint — must be module-level for pickling on Windows."""
    cache_path, key, value = args
    # Reconstruct minimal Settings without going through env.
    s = Settings(redis_url=None)
    object.__setattr__(s, "cache_file", Path(cache_path))
    object.__setattr__(s, "source_status_file", Path(cache_path).parent / "status.json")
    save_cache(value, key=key, settings=s)


def test_save_cache_is_atomic_and_preserves_siblings(tmp_path: Path) -> None:
    settings = _build_settings(tmp_path)

    # Seed one key so we can verify the second writer doesn't wipe it.
    save_cache({"v": "a"}, key="alpha", settings=settings)
    save_cache({"v": "b"}, key="beta", settings=settings)

    assert load_cache("alpha", settings) == {"v": "a"}
    assert load_cache("beta", settings) == {"v": "b"}

    # Verify on disk that both keys survived.
    with settings.cache_file.open("r", encoding="utf-8") as handle:
        payload = json.load(handle)
    assert set(payload.keys()) == {"alpha", "beta"}


def test_concurrent_writes_do_not_lose_keys(tmp_path: Path) -> None:
    settings = _build_settings(tmp_path)
    cache_path = str(settings.cache_file)

    tasks = [(cache_path, f"key_{i}", {"i": i}) for i in range(8)]

    # Spawn pool (Windows requires spawn). Each child writes one key.
    ctx = mp.get_context("spawn")
    with ctx.Pool(processes=4) as pool:
        pool.map(_writer, tasks)

    # All 8 keys must be present in the final file.
    final = json.loads(settings.cache_file.read_text(encoding="utf-8"))
    for i in range(8):
        assert f"key_{i}" in final, f"key_{i} was lost in concurrent write"
        assert final[f"key_{i}"]["value"] == {"i": i}


def test_corrupted_cache_resets_gracefully(tmp_path: Path) -> None:
    settings = _build_settings(tmp_path)
    settings.cache_file.parent.mkdir(parents=True, exist_ok=True)
    settings.cache_file.write_text("{ not json", encoding="utf-8")

    # load returns None instead of raising
    assert load_cache("anything", settings) is None
    # save replaces the file cleanly
    save_cache({"v": "ok"}, key="recover", settings=settings)
    assert load_cache("recover", settings) == {"v": "ok"}
