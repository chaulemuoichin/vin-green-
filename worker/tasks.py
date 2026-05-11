from __future__ import annotations

import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

from hanoi_air.alerts import post_alerts
from hanoi_air.config import get_settings
from hanoi_air.forecast import build_cached_forecast
from hanoi_air.observability import init_sentry

init_sentry(service="worker")

try:
    from celery import Celery
except Exception:  # pragma: no cover
    Celery = None  # type: ignore


settings = get_settings()
if Celery is not None:
    celery_app = Celery(
        "hanoi_air",
        broker=settings.redis_url or "redis://localhost:6379/0",
        backend=settings.redis_url or "redis://localhost:6379/0",
    )
    celery_app.conf.beat_schedule = {
        "refresh-hanoi-air-30min": {
            "task": "worker.tasks.refresh_forecast",
            "schedule": 1800.0,
        },
        "cleanup-raw-archive-daily": {
            "task": "worker.tasks.cleanup_archive",
            "schedule": 86400.0,  # once a day
        },
    }
else:
    celery_app = None


def _refresh() -> dict:
    bundle = build_cached_forecast(settings, force_refresh=True, use_live=settings.use_live_data)
    post_alerts(
        [
            type("AlertProxy", (), {"to_dict": lambda self, item=item: item})()
            for item in bundle["alerts"]
        ],
        settings.alert_webhook_url,
    )
    return {"generated_at": bundle["generated_at"], "alerts": len(bundle["alerts"])}


def _cleanup_archive(raw_days: int = 7, processed_days: int = 90) -> dict:
    """Delete raw API archives older than ``raw_days``. Run daily."""
    from scripts.cleanup_raw_archive import cleanup_dir  # local import keeps import graph small

    raw_files, raw_bytes = cleanup_dir(settings.raw_dir, raw_days, dry_run=False)
    proc_files, proc_bytes = cleanup_dir(settings.processed_dir, processed_days, dry_run=False)
    return {
        "raw_files_removed": raw_files,
        "raw_bytes_freed": raw_bytes,
        "processed_files_removed": proc_files,
        "processed_bytes_freed": proc_bytes,
    }


if celery_app is not None:

    @celery_app.task(name="worker.tasks.refresh_forecast")
    def refresh_forecast() -> dict:
        return _refresh()

    @celery_app.task(name="worker.tasks.cleanup_archive")
    def cleanup_archive() -> dict:
        return _cleanup_archive()

else:

    def refresh_forecast() -> dict:
        return _refresh()

    def cleanup_archive() -> dict:
        return _cleanup_archive()
