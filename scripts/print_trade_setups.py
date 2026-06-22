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
  cols = ["symbol", "style", "status", "direction", "entry", "stop_loss", "tp1", "tp2", "rr_tp2"]
  header = f"{'Symbol':<12} {'Style':<10} {'Status':<12} {'Dir':<6} {'Entry':<12} {'Stop':<12} {'TP1':<12} {'RR':<6}"
  print(header)
  print("-" * len(header))
  for r in rows[:limit]:
    print(
      f"{r.get('symbol', ''):<12} {r.get('style', ''):<10} {r.get('status', ''):<12} "
      f"{r.get('direction', ''):<6} {str(r.get('entry', '')):<12} {str(r.get('stop_loss', '')):<12} "
      f"{str(r.get('tp1', '')):<12} {str(r.get('rr_tp2', '')):<6}"
    )
  print(f"\n({min(limit, len(rows))} of {len(rows)} rows)")


def main() -> None:
  p = argparse.ArgumentParser(description="Print trade setups to terminal")
  p.add_argument("--csv", default="output/latest_setups.csv")
  p.add_argument("--status", choices=["executable", "monitor", "not_actionable"])
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
    csv_path = Path("output/latest_setups.csv")
    if not csv_path.exists():
      csv_path = Path(prefix.replace("_full_", "_setups_") + ".csv")

  if not csv_path.exists():
    print(f"Missing {csv_path}. Run batch first.", file=sys.stderr)
    sys.exit(1)

  rows = _load_rows(csv_path, args.status)
  print(f"Trade setups from {csv_path.resolve()}\n")
  _print_table(rows, args.limit)
  md = Path("reports/TRADE_SETUPS.md")
  if md.exists():
    print(f"\nMarkdown table: {md.resolve()}")


if __name__ == "__main__":
  main()
