#!/usr/bin/env python3
"""Track calibrated-era ledger accumulation and trigger clean-subset re-estimation."""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

from engine.indicator_calibration import (
  accumulation_status,
  merge_setup_metadata_into_trades,
  run_calibration_accumulation_cycle,
  run_indicator_calibration,
)
from engine.paper_trading import (
  append_paper_ledger,
  apply_honesty_adjustments,
  apply_paper_to_results,
  run_paper_batch,
)


def _find_latest_json(output_dir: Path) -> Path | None:
  candidates = sorted(output_dir.glob("top*_analysis_*.json"), reverse=True)
  return candidates[0] if candidates else None


def _print_status(status: dict) -> None:
  print("\n=== Calibration accumulation ===")
  print(f"  Total closed:     {status.get('total_closed')}")
  print(f"  Legacy closed:    {status.get('legacy_closed')}")
  print(f"  Calibrated closed:{status.get('calibrated_closed')} / {status.get('target_closed')}")
  print(f"  Remaining:        {status.get('remaining_to_target')}")
  print(f"  Calibrated WR:    {status.get('calibrated_win_rate')}")
  print(f"  Ready for clean:  {status.get('ready_for_clean_reestimate')}")
  print(f"  Current cal id:   {status.get('current_calibration_id')}")
  print(f"  Generation:       {status.get('current_generation')} ({status.get('current_source')})")
  if status.get("next_action"):
    print(f"  Next:             {status['next_action']}")
  if status.get("reestimated"):
    cal = status.get("calibration", {})
    print(
      f"\n  Re-estimated: gen={cal.get('generation')} source={cal.get('source')} "
      f"baseline={cal.get('baseline_win_rate')} kept={cal.get('kept_signals')}"
    )


def main() -> int:
  p = argparse.ArgumentParser(description="Calibrated-era trade accumulation + clean re-estimate")
  p.add_argument("--status", action="store_true", help="Show accumulation status only")
  p.add_argument("--paper", action="store_true", help="Run paper batch on latest JSON first")
  p.add_argument("--json", type=str, help="Batch JSON for --paper (default: latest)")
  p.add_argument("--reestimate", action="store_true", help="Force clean-subset re-estimation now")
  p.add_argument("--bootstrap", action="store_true", help="Re-run bootstrap calibration from all ledger")
  args = p.parse_args()

  if args.bootstrap:
    cal = run_indicator_calibration(calibrated_only=False)
    print(f"Bootstrap calibration: source={cal.get('source')} closed={cal.get('closed_trades')}")
    if not cal.get("available"):
      print(f"  Skipped: {cal.get('reason')}", file=sys.stderr)
      return 1
    return 0

  if args.status and not args.paper and not args.reestimate:
    _print_status(accumulation_status())
    return 0

  results = None
  trades = None
  if args.paper:
    json_path = Path(args.json) if args.json else _find_latest_json(Path("output"))
    if not json_path or not json_path.exists():
      print("No batch JSON found. Run scripts/run_top50_batch.py first.", file=sys.stderr)
      return 1
    print(f"[accumulation] Paper batch on {json_path}")
    results = json.loads(json_path.read_text())
    report = run_paper_batch(results, fetch_missing=True)
    results = apply_paper_to_results(results, report)
    for r in results:
      if r.get("status") != "incomplete" and r.get("step8_outcomes"):
        r["step8_outcomes"] = apply_honesty_adjustments(r["step8_outcomes"])
    trades = merge_setup_metadata_into_trades(report.get("trades", []), results)
    append_paper_ledger(trades)
    json_path.write_text(json.dumps(results, indent=2, default=str))
    print(f"  Appended {len(trades)} trades ({sum(1 for t in trades if t.get('scoring_era')=='calibrated')} calibrated-era)")

  status = run_calibration_accumulation_cycle(
    results=results,
    trades=trades,
    force_reestimate=args.reestimate,
  )
  _print_status(status)
  return 0


if __name__ == "__main__":
  raise SystemExit(main())
