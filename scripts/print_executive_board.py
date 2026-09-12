#!/usr/bin/env python3
"""Executive trade board — ranked actionable pairs × timeframes, always."""

from __future__ import annotations

import argparse
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from engine.accurate_setups import find_latest_analysis_json, load_results_json
from engine.executive_board import build_executive_board, save_executive_board


def main() -> int:
  p = argparse.ArgumentParser(description="Executive trade board — solution provider picks")
  p.add_argument("--json", help="Batch analysis JSON")
  p.add_argument("--per-tf", type=int, default=5, help="Picks per timeframe")
  p.add_argument("--max", type=int, default=30, help="Max total board picks")
  args = p.parse_args()

  json_path = Path(args.json) if args.json else find_latest_analysis_json()
  if not json_path or not json_path.exists():
    print("Run: PYTHONPATH=/workspace python3 scripts/run_top50_batch.py -n 50", file=sys.stderr)
    return 1

  board = build_executive_board(
    load_results_json(json_path),
    picks_per_tf=args.per_tf,
    max_total=args.max,
  )
  paths = save_executive_board(board)

  print(f"Source: {json_path}")
  print(f"Scored setups: {board['total_scored']}")
  print(f"Board picks: {board['board_picks']}")
  print(f"By action: {board['by_action']}")
  print(f"By timeframe: {board['by_timeframe']}")
  print(f"JSON: {paths['json']}")
  print(f"CSV:  {paths['csv']}\n")

  print("=" * 90)
  print(f"{'ACTION':<18} {'SCORE':>5}  {'SYMBOL':<12} {'TF':<4} {'DIR':<5} {'SIZE':>4}  ENTRY / STOP / RR")
  print("=" * 90)
  for p in board.get("picks", []):
    print(
      f"{p['executive_action']:<18} {p['executive_score']:>5}  "
      f"{p['symbol']:<12} {p['timeframe']:<4} {p['direction']:<5} {p['position_size_pct']:>3}%  "
      f"{p.get('entry')} / {p.get('stop_loss')} / {p.get('rr_tp2')}"
    )
    print(f"    {p.get('playbook', '')[:85]}")

  return 0


if __name__ == "__main__":
  raise SystemExit(main())
