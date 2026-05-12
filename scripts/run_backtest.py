"""CLI: backtest the forecast against archived station readings.

Usage:
    python scripts/run_backtest.py --days 7
    python scripts/run_backtest.py --days 7 --model ensemble --json

Writes a snapshot JSON to data/processed/backtest_<ts>.json that the
Streamlit "Độ chính xác" tab will read.
"""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

from hanoi_air.config import get_settings  # noqa: E402
from hanoi_air.validation import backtest, save_backtest  # noqa: E402


def _format_markdown_table(result: dict) -> str:
    if result.get("status") != "ok":
        return f"_No backtest available — {result.get('note') or result.get('status')}_"
    overall = result["overall"]
    fc = overall["forecast"]
    base = overall["persistence_baseline"]
    lines = [
        "# Backtest summary",
        "",
        f"- **Model:** `{result['model']}` · window: {result['days']} day(s) · "
        f"samples: {fc['n']}",
        f"- **Generated:** {result['generated_at']}",
        "",
        "## Overall",
        "",
        "| Predictor | RMSE | MAE | R² | MBE | n |",
        "|---|---:|---:|---:|---:|---:|",
        f"| Forecast | {fc['rmse']} | {fc['mae']} | {fc['r2']} | {fc['mbe']} | {fc['n']} |",
        f"| Persistence baseline | {base['rmse']} | {base['mae']} | {base['r2']} | "
        f"{base['mbe']} | {base['n']} |",
        "",
    ]
    improvement = overall.get("rmse_improvement_vs_persistence")
    if improvement is not None:
        sign = "+" if improvement > 0 else ""
        lines.append(f"Forecast beats persistence on RMSE by **{sign}{improvement}** µg/m³.\n")

    lines += ["## Per district", "",
              "| District | Actual | Forecast | Persistence | |error| (fc) | |error| (pers) |",
              "|---|---:|---:|---:|---:|---:|"]
    rows = sorted(result["per_district"], key=lambda r: r["abs_error"], reverse=True)
    for row in rows:
        lines.append(
            f"| {row['district_id']} | {row['actual_pm25']} | {row['forecast_pm25']} | "
            f"{row['persistence_pm25']} | {row['abs_error']} | {row['persistence_abs_error']} |"
        )
    return "\n".join(lines)


def main() -> int:
    parser = argparse.ArgumentParser(description="Hanoi Air Forecast backtest CLI")
    parser.add_argument("--days", type=int, default=7,
                        help="Days of archived readings to compare against (default: 7)")
    parser.add_argument("--model", choices=("heuristic", "ensemble"), default="heuristic")
    parser.add_argument("--no-save", action="store_true",
                        help="Skip writing data/processed/backtest_*.json")
    parser.add_argument("--json", action="store_true", help="Emit raw JSON instead of markdown")
    args = parser.parse_args()

    settings = get_settings()
    result = backtest(settings=settings, days=args.days, model=args.model)

    if not args.no_save and result.get("status") == "ok":
        path = save_backtest(result, settings=settings)
        result["_snapshot_path"] = str(path)

    if args.json:
        print(json.dumps(result, ensure_ascii=False, indent=2))
    else:
        print(_format_markdown_table(result))

    return 0 if result.get("status") in ("ok", "no_data", "no_overlap") else 1


if __name__ == "__main__":
    sys.exit(main())
