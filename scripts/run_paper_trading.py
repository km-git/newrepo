#!/usr/bin/env python3
"""Run paper trading + historical analysis on batch results or latest JSON."""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

from engine.full_report import export_all_reports, regenerate_from_json
from engine.paper_trading import (
  append_paper_ledger,
  apply_honesty_adjustments,
  apply_paper_to_results,
  run_paper_batch,
  save_paper_csv,
  save_paper_metrics,
)
from engine.autodream import build_monitor_queue, save_monitor_queue


def _find_latest_json(output_dir: Path) -> Path | None:
  candidates = sorted(output_dir.glob("top*_analysis_*.json"), reverse=True)
  return candidates[0] if candidates else None


def main() -> int:
  p = argparse.ArgumentParser(description="Paper trade all setups with historical analysis")
  p.add_argument("--json", type=str, help="Batch JSON path (default: latest in output/)")
  p.add_argument("--no-fetch", action="store_true", help="Skip OHLCV refetch (only if data embedded)")
  p.add_argument("--regenerate", action="store_true", help="Regenerate CSV/HTML/MD reports after paper run")
  args = p.parse_args()

  json_path = Path(args.json) if args.json else _find_latest_json(Path("output"))
  if not json_path or not json_path.exists():
    print("No batch JSON found. Run scripts/run_top50_batch.py first.", file=sys.stderr)
    return 1

  print(f"[paper] Loading {json_path}")
  results = json.loads(json_path.read_text())
  report = run_paper_batch(results, fetch_missing=not args.no_fetch)
  results = apply_paper_to_results(results, report)
  for r in results:
    if r.get("status") != "incomplete" and r.get("step8_outcomes"):
      r["step8_outcomes"] = apply_honesty_adjustments(r["step8_outcomes"])

  json_path.write_text(json.dumps(results, indent=2, default=str))
  append_paper_ledger(report.get("trades", []))
  metrics = save_paper_metrics(report)
  csv_path = save_paper_csv(report)
  save_monitor_queue(build_monitor_queue(results))

  print(f"\n[paper] DONE — {report.get('setups_papered')} setups papered")
  print(f"  Closed:   {report.get('closed_trades')}  Open: {report.get('open_trades')}")
  print(f"  Win rate: {report.get('win_rate')}")
  print(f"  Avg PnL:  {report.get('avg_pnl_r')}R (tier-sized)")
  print(f"  Metrics:  {metrics}")
  print(f"  CSV:      {csv_path}")
  print(f"  By style: {json.dumps(report.get('by_style', {}), indent=2)}")
  print(f"  By tier:  {json.dumps(report.get('by_tier', {}), indent=2)}")

  if args.regenerate:
    regenerate_from_json(str(json_path))
    export_all_reports(results, "output/latest_paper_refresh", title="Paper Refresh")
    print("  Reports regenerated.")

  return 0


if __name__ == "__main__":
  raise SystemExit(main())
