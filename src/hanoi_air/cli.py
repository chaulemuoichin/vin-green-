from __future__ import annotations

import argparse
from collections.abc import Iterable

from .config import get_settings
from .forecast import build_cached_forecast, top_n_worst


def format_top5(rows: Iterable[dict]) -> str:
    lines = ["rank,district,timestamp,aqi,pm25,no2,category"]
    for idx, row in enumerate(rows, 1):
        lines.append(
            f"{idx},{row['district_name']},{row['timestamp']},{row['aqi']},"
            f"{row['pm25']},{row['no2']},{row['category']}"
        )
    return "\n".join(lines)


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Hanoi air forecast utilities")
    sub = parser.add_subparsers(dest="command")
    top5 = sub.add_parser("top5", help="Print tomorrow's five worst districts")
    top5.add_argument("--refresh", action="store_true", help="Recompute instead of using cache")
    top5.add_argument("--sample", action="store_true", help="Disable live API calls")
    args = parser.parse_args(argv)

    if args.command == "top5":
        settings = get_settings()
        bundle = build_cached_forecast(
            settings, force_refresh=args.refresh, use_live=not args.sample
        )
        print(format_top5(top_n_worst(bundle, 5)))
        return 0
    parser.print_help()
    return 1


if __name__ == "__main__":
    raise SystemExit(main())
