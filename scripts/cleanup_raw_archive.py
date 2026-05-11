"""Delete raw API archives older than N days.

The pipeline writes one file per API call into ``data/raw/{source}/YYYY-MM-DD/``.
Over time this grows unbounded — a single SOMO crawl is ~50KB but we hit it
every 30 min, so ~2.4MB/day. Keep last 7 days raw + 90 days processed by
default; tune via env or CLI flags.

Usage:

    python scripts/cleanup_raw_archive.py                  # delete >7d raw
    python scripts/cleanup_raw_archive.py --dry-run        # report only
    python scripts/cleanup_raw_archive.py --raw-days 14    # custom retention
    python scripts/cleanup_raw_archive.py --include-processed  # also processed/

Returns exit 0 always (idempotent maintenance).
"""

from __future__ import annotations

import argparse
import sys
from datetime import datetime, timedelta, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

from hanoi_air.config import get_settings
from hanoi_air.logging_setup import configure_logging, get_logger

configure_logging(level="INFO")
logger = get_logger(__name__)


def _parse_iso_dir(name: str) -> datetime | None:
    """Parse a YYYY-MM-DD directory name. Return None if it doesn't match."""
    try:
        return datetime.strptime(name, "%Y-%m-%d").replace(tzinfo=timezone.utc)
    except ValueError:
        return None


def cleanup_dir(root: Path, max_age_days: int, *, dry_run: bool) -> tuple[int, int]:
    """Walk ``root`` removing date-named subdirs older than ``max_age_days``.

    Returns (files_removed, bytes_freed).
    """
    if not root.exists():
        logger.info("no archive at {root}; skipping", root=root)
        return (0, 0)

    cutoff = datetime.now(timezone.utc) - timedelta(days=max_age_days)
    files_removed = 0
    bytes_freed = 0

    for source_dir in sorted(root.iterdir()):
        if not source_dir.is_dir():
            continue
        for day_dir in sorted(source_dir.iterdir()):
            if not day_dir.is_dir():
                continue
            day = _parse_iso_dir(day_dir.name)
            if day is None or day >= cutoff:
                continue
            day_files = list(day_dir.glob("*"))
            day_bytes = sum(f.stat().st_size for f in day_files if f.is_file())
            logger.info(
                "{action} {src}/{day} ({n} files, {kb:.0f} KB)",
                action="DRY-RUN would remove" if dry_run else "removing",
                src=source_dir.name,
                day=day_dir.name,
                n=len(day_files),
                kb=day_bytes / 1024.0,
            )
            if not dry_run:
                for f in day_files:
                    f.unlink(missing_ok=True)
                day_dir.rmdir()
            files_removed += len(day_files)
            bytes_freed += day_bytes

    return files_removed, bytes_freed


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--raw-days", type=int, default=7)
    parser.add_argument("--processed-days", type=int, default=90)
    parser.add_argument("--include-processed", action="store_true")
    parser.add_argument("--dry-run", action="store_true")
    args = parser.parse_args()

    settings = get_settings()

    raw_files, raw_bytes = cleanup_dir(settings.raw_dir, args.raw_days, dry_run=args.dry_run)
    logger.info(
        "raw archive: {f} files, {mb:.1f} MB {verb}",
        f=raw_files,
        mb=raw_bytes / (1024 * 1024),
        verb="would be freed" if args.dry_run else "freed",
    )

    if args.include_processed:
        proc_files, proc_bytes = cleanup_dir(
            settings.processed_dir, args.processed_days, dry_run=args.dry_run
        )
        logger.info(
            "processed archive: {f} files, {mb:.1f} MB {verb}",
            f=proc_files,
            mb=proc_bytes / (1024 * 1024),
            verb="would be freed" if args.dry_run else "freed",
        )

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
