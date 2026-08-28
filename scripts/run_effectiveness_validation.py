#!/usr/bin/env python3
"""Run comprehensive effectiveness validation and emit pass/fail report."""

from __future__ import annotations

import argparse
import json
import sys


def main() -> None:
  parser = argparse.ArgumentParser(description="Validate trading system effectiveness")
  parser.add_argument("--no-tests", action="store_true", help="Skip pytest subset")
  parser.add_argument("--resolve-open", action="store_true", help="Resolve all open tracked setups (slow)")
  parser.add_argument("--no-paper", action="store_true", help="Skip paper simulation")
  parser.add_argument("--no-fetch", action="store_true", help="Paper sim without OHLC fetch")
  parser.add_argument("--equity", type=float, default=50_000.0)
  parser.add_argument("--csv", default="", help="Limit orders CSV for paper sim")
  parser.add_argument("--max-positions", type=int, default=0, help="Override paper max positions")
  parser.add_argument("--fast", action="store_true", help="Skip live paper sim (metrics + tracked backtest only)")
  parser.add_argument("--json", action="store_true", help="Print full JSON report")
  args = parser.parse_args()

  from engine.effectiveness_validation import run_effectiveness_validation

  report = run_effectiveness_validation(
    run_tests=not args.no_tests,
    run_learning=args.resolve_open,
    run_paper=not args.no_paper and not args.fast,
    fetch_ohlc=not args.no_fetch,
    equity=args.equity,
    csv_path=args.csv,
    paper_max_positions=args.max_positions,
  )

  if args.json:
    print(json.dumps(report.to_dict(), indent=2, default=str))
  else:
    print(f"\n{'='*60}")
    print(f"EFFECTIVENESS: {'PASS' if report.ok else 'FAIL'} — {report.summary}")
    print(f"{'='*60}\n")
    print(f"{'Gate':<28} {'Status':<8} Value")
    print("-" * 60)
    for g in report.gates:
      status = "PASS" if g.passed else "FAIL"
      val = g.value
      if isinstance(val, dict):
        val = json.dumps(val, default=str)[:40]
      print(f"{g.name:<28} {status:<8} {val}")
    print(f"\nReports: reports/EFFECTIVENESS_VALIDATION.md")
    print(f"         output/system/effectiveness_latest.json")

  sys.exit(0 if report.ok else 1)


if __name__ == "__main__":
  main()
