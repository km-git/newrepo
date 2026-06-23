#!/usr/bin/env python3
"""Print all research setups (200 rows) with honest tiers — full pair × TF visibility."""

from __future__ import annotations

import argparse
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from engine.accurate_setups import (
  extract_research_setups,
  find_latest_analysis_json,
  load_results_json,
  save_research_setups_csv,
  summarize_research,
)


def main() -> int:
  p = argparse.ArgumentParser(description="All research setups with honest tiers")
  p.add_argument("--json", help="Batch JSON path")
  p.add_argument("--tier", default=None,
                 help="Filter: tradeable, high_watch, validated_monitor, conditional, speculative")
  p.add_argument("--csv", default="output/latest_research_setups.csv")
  p.add_argument("--limit", type=int, default=40)
  args = p.parse_args()

  json_path = Path(args.json) if args.json else find_latest_analysis_json()
  if not json_path or not json_path.exists():
    print("Run: PYTHONPATH=/workspace python3 scripts/run_top50_batch.py -n 50", file=sys.stderr)
    return 1

  all_rows = extract_research_setups(load_results_json(json_path))
  rows = [r for r in all_rows if r["research_tier"] == args.tier] if args.tier else all_rows
  summary = summarize_research(all_rows)
  save_research_setups_csv(all_rows, args.csv)

  print(f"Source: {json_path}")
  print(f"Total setups: {summary['total']} (50 pairs × 4 timeframes)")
  print(f"By research tier: {summary['by_research_tier']}")
  print(f"Pipeline status: {summary['by_pipeline_status']}")
  print(f"CSV: {args.csv}\n")

  show = rows if args.tier else all_rows
  by_tier: dict[str, list] = {}
  for r in show:
    by_tier.setdefault(r["research_tier"], []).append(r)

  labels = {
    "tradeable": "TRADEABLE",
    "high_watch": "HIGH WATCH",
    "validated_monitor": "VALIDATED MONITOR",
    "conditional": "CONDITIONAL",
    "speculative": "SPECULATIVE",
  }
  for tier_key, label in labels.items():
    subset = by_tier.get(tier_key, [])
    if not subset:
      continue
    print(f"\n=== {label} ({len(subset)}) ===")
    for r in subset[: args.limit]:
      oos = r.get("oos_win_rate")
      on = r.get("oos_trades")
      oos_s = f"{float(oos):.0%}({on})" if oos is not None and on else "n/a"
      print(
        f"{r['symbol']:<12} {r['timeframe']:<4} {r['direction']:<5} "
        f"{r['pipeline_status']:<12} {str(r['execution_tier']):<5} "
        f"rd={int(r.get('readiness_score') or 0):>2} OOS={oos_s:<9} "
        f"entry={r.get('entry')} stop={r.get('stop_loss')} RR={r.get('rr_tp2')}"
      )

  return 0


if __name__ == "__main__":
  raise SystemExit(main())
