#!/usr/bin/env python3
"""Find and print accurate trade setups for all pairs and style timeframes."""

from __future__ import annotations

import argparse
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from engine.accurate_setups import (
  extract_accurate_setups,
  find_latest_analysis_json,
  load_results_json,
  save_accurate_setups_csv,
  summarize_accurate,
)


def _print_row(r: dict) -> None:
  oos = r.get("oos_win_rate")
  oos_n = r.get("oos_trades")
  oos_s = f"{float(oos):.0%}({oos_n})" if oos is not None and oos_n else "n/a"
  print(
    f"{r['accuracy_tier']} {r['accuracy_score']:3d} "
    f"{r['symbol']:<12} {r['style']:<10} {r['timeframe']:<4} "
    f"{r['status']:<14} {str(r['execution_tier']):<5} "
    f"{r['direction']:<5} rd={int(r.get('readiness_score') or 0):>2} "
    f"OOS={oos_s:<10} entry={r.get('entry')} stop={r.get('stop_loss')} "
    f"RR={r.get('rr_tp2')}"
  )
  print(f"     tags: {r.get('tags')}")
  print(f"     {str(r.get('honest_reason', ''))[:120]}")


def main() -> int:
  p = argparse.ArgumentParser(description="Accurate setups across all pairs × timeframes")
  p.add_argument("--json", help="Batch analysis JSON (default: latest top50)")
  p.add_argument("--tier", choices=["A", "B", "C"], default="C", help="Minimum accuracy tier")
  p.add_argument("--limit", type=int, default=50)
  p.add_argument("--csv", default="output/latest_accurate_setups.csv")
  args = p.parse_args()

  json_path = Path(args.json) if args.json else find_latest_analysis_json()
  if not json_path or not json_path.exists():
    print("No analysis JSON. Run: PYTHONPATH=/workspace python3 scripts/run_top50_batch.py -n 50", file=sys.stderr)
    return 1

  results = load_results_json(json_path)
  rows = extract_accurate_setups(results, min_tier=args.tier)
  summary = summarize_accurate(rows)
  csv_path = save_accurate_setups_csv(rows, args.csv)

  pairs = len({r["symbol"] for r in results if r.get("status") != "incomplete"})
  print(f"Source: {json_path}")
  print(f"Pairs: {pairs} | Timeframes: scalp=15m, day_trade=1h, swing=1d, long_term=1w")
  print(f"Accurate setups (tier>={args.tier}): {summary['total_accurate']}")
  print(f"  Tier A (tradeable): {summary['by_tier'].get('A', 0)}")
  print(f"  Tier B (high watch): {summary['by_tier'].get('B', 0)}")
  print(f"  Tier C (validated): {summary['by_tier'].get('C', 0)}")
  print(f"  Executable: {summary['executable_count']}")
  print(f"CSV: {csv_path}\n")

  for label, subset in [
    ("TIER A — TRADEABLE", summary["tier_a"]),
    ("TIER B — HIGH CONFIDENCE WATCH", summary["tier_b"]),
    ("TIER C — VALIDATED MONITOR", summary["tier_c"]),
  ]:
    if not subset:
      continue
    print(f"\n{'='*70}\n{label} ({len(subset)})\n{'='*70}")
    for r in subset[: args.limit]:
      _print_row(r)

  return 0


if __name__ == "__main__":
  raise SystemExit(main())
