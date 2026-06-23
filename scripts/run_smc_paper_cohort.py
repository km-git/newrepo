#!/usr/bin/env python3
"""Paper-trade SMC FULL + PROBE executables at reduced cohort size."""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

from engine.smc_paper_cohort import run_and_persist_smc_cohort


def _find_latest_json(output_dir: Path) -> Path | None:
  candidates = sorted(output_dir.glob("top*_analysis_*.json"), reverse=True)
  for p in candidates:
    if "top50" in p.name or "top20" in p.name:
      return p
  return candidates[0] if candidates else None


def main() -> int:
  p = argparse.ArgumentParser(description="SMC paper cohort — FULL 50% / PROBE 25%")
  p.add_argument("--json", type=str, help="Batch JSON (default: latest top50)")
  p.add_argument("--no-fetch", action="store_true", help="Skip OHLCV refetch")
  args = p.parse_args()

  json_path = Path(args.json) if args.json else _find_latest_json(Path("output"))
  if not json_path or not json_path.exists():
    print("No batch JSON found. Run scripts/run_top50_batch.py first.", file=sys.stderr)
    return 1

  print(f"[smc-cohort] Loading {json_path}")
  results = json.loads(json_path.read_text())
  report = run_and_persist_smc_cohort(results, fetch_missing=not args.no_fetch)

  print(f"\n[smc-cohort] {report['cohort_id']}")
  print(f"  FULL:  {report['full_count']} @ {report['size_policy']['full']:.0%} size")
  print(f"  PROBE: {report['probe_count']} @ {report['size_policy']['probe']:.0%} size")
  print(f"  Papered: {report['papered']}  Closed: {report['closed_trades']}  Open: {report['open_trades']}")
  if report.get("win_rate") is not None:
    print(f"  Cohort WR: {report['win_rate']:.1%}  Avg PnL: {report.get('avg_pnl_r')}R")

  print("\n  Executables:")
  for e in report.get("executables", []):
    print(
      f"    {e['symbol']:14} {e['tier']:5} grade={e['grade']} "
      f"{e['tf']:4} {e['direction']:5} size={e['size_pct']}%"
    )

  print("\n  Trades:")
  for t in report.get("trades", []):
    if not t.get("available"):
      print(f"    {t['symbol']:14} SKIP — {t.get('reason')}")
      continue
    focus = [k for k, v in (t.get("focus_tokens") or {}).items() if v]
    print(
      f"    {t['symbol']:14} {t.get('execution_tier'):5} "
      f"{t.get('paper_outcome', '?'):5} {t.get('paper_pnl_r', 0):+.2f}R "
      f"size={t.get('cohort_size_pct')}% tokens={focus[:3]}"
    )

  lift = report.get("token_lift_all_smc") or {}
  if lift.get("available"):
    print(f"\n  Token lift (all SMC ledger, n={lift['closed_trades']}, baseline={lift['baseline_win_rate']:.1%}):")
    for row in lift.get("ranked_by_lift", [])[:6]:
      print(
        f"    {row['token']:22} n={row['samples']:3} "
        f"WR={row['win_rate']:.1%} lift={row['lift_vs_baseline']:+.1%} "
        f"WilsonLB={row['wilson_lb']:.1%}"
      )
  else:
    print(f"\n  Token lift: {lift.get('reason', 'pending more closed trades')}")

  acc = report.get("calibration_accumulation") or {}
  print(f"\n  Calibration: gen={acc.get('current_generation')} "
        f"calibrated_closed={acc.get('calibrated_closed')} "
        f"ready_reestimate={acc.get('ready_for_clean_reestimate')}")
  print(f"  Saved: {report.get('paths', {})}")

  return 0


if __name__ == "__main__":
  raise SystemExit(main())
