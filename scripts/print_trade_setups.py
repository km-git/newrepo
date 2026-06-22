#!/usr/bin/env python3
"""Print trade setups table to terminal (from latest CSV or regenerate)."""

from __future__ import annotations

import argparse
import csv
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))


def _load_rows(path: Path, status: str | None) -> list[dict]:
  with path.open() as f:
    rows = list(csv.DictReader(f))
  if status:
    rows = [r for r in rows if r.get("status") == status]
  return rows


def _print_table(rows: list[dict], limit: int) -> None:
  cols = ["symbol", "style", "status", "execution_tier", "readiness_score", "direction",
          "entry", "stop_loss", "tp1", "rr_tp2", "1d_structure", "consensus", "honest_reason"]
  header = f"{'Symbol':<12} {'Style':<10} {'Status':<14} {'Tier':<6} {'Rd':>3} {'Dir':<5} {'Entry':<10} {'1d EW':<20} {'Reason':<30}"
  print(header)
  print("-" * len(header))
  for r in rows[:limit]:
    reason = str(r.get("honest_reason", ""))[:28]
    print(
      f"{r.get('symbol', ''):<12} {r.get('style', ''):<10} {r.get('status', ''):<14} "
      f"{str(r.get('execution_tier', '')):<6} {int(float(r.get('readiness_score') or 0)):>3} "
      f"{r.get('direction', ''):<5} {str(r.get('entry', ''))[:10]:<10} "
      f"{str(r.get('1d_structure', ''))[:20]:<20} {reason}"
    )
  print(f"\n({min(limit, len(rows))} of {len(rows)} rows)")


def main() -> None:
  p = argparse.ArgumentParser(description="Print trade setups to terminal")
  p.add_argument("--csv", default="output/latest_setups_complete.csv")
  p.add_argument("--status", choices=["executable", "monitor", "not_actionable"],
                 help="Filter by status (default: show ALL)")
  p.add_argument("--limit", type=int, default=40)
  p.add_argument("--regenerate", action="store_true", help="Rebuild from latest analysis JSON")
  args = p.parse_args()

  csv_path = Path(args.csv)
  if args.regenerate or not csv_path.exists():
    import json
    from engine.full_report import export_all_reports

    out = Path("output")
    jsons = sorted(out.glob("top*_analysis_*.json"), key=lambda p: p.stat().st_mtime, reverse=True)
    if not jsons:
      print("No analysis JSON found. Run: scripts/run_top50_batch.py -n 50", file=sys.stderr)
      sys.exit(1)
    results = json.loads(jsons[0].read_text())
    prefix = str(out / jsons[0].stem.replace("_analysis", "_full"))
    export_all_reports(results, prefix, title=f"Trade Setups — {len(results)} pairs")
    csv_path = Path("output/latest_setups_complete.csv")
    if not csv_path.exists():
      csv_path = Path(prefix.replace("_full_", "_setups_") + ".csv")

  if not csv_path.exists():
    print(f"Missing {csv_path}. Run batch first.", file=sys.stderr)
    sys.exit(1)

  rows = _load_rows(csv_path, args.status)
  from collections import Counter
  counts = Counter(r.get("status") for r in _load_rows(csv_path, None))
  print(f"Trade setups from {csv_path.resolve()}")
  print(f"Counts: {dict(counts)} — showing {len(rows)} rows\n")
  _print_table(rows, args.limit)
  md = Path("reports/TRADE_SETUPS.md")
  if md.exists():
    print(f"\nMarkdown table: {md.resolve()}")


if __name__ == "__main__":
  main()
