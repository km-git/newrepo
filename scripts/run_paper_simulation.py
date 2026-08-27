#!/usr/bin/env python3
"""Run OHLC-based paper execution simulation on limit order export."""

from __future__ import annotations

import argparse
import json
import os
import sys


def main() -> None:
  parser = argparse.ArgumentParser(description="Paper simulate limit fills on OHLC")
  parser.add_argument("--csv", default="", help="Limit orders CSV (default: output/latest...)")
  parser.add_argument("--equity", type=float, default=0, help="Starting equity USD")
  parser.add_argument("--max-positions", type=int, default=0, help="Override EW_PAPER_MAX_POSITIONS")
  parser.add_argument("--no-fetch", action="store_true", help="Skip OHLC fetch (dry structural test)")
  parser.add_argument("--no-kill-zone", action="store_true", help="Allow setups outside kill zone")
  parser.add_argument("--json", action="store_true", help="Print full JSON summary")
  args = parser.parse_args()

  if args.max_positions:
    os.environ["EW_PAPER_MAX_POSITIONS"] = str(args.max_positions)
  if args.no_kill_zone:
    os.environ["EW_PAPER_REQUIRE_KILL_ZONE"] = "0"

  from engine.paper_simulator import run_paper_simulation

  summary = run_paper_simulation(
    csv_path=args.csv,
    equity_usd=args.equity or None,
    fetch_ohlc=not args.no_fetch,
  )

  if args.json:
    print(json.dumps(summary, indent=2, default=str))
  else:
    print(f"Paper P&L: ${summary.get('realized_pnl_usd', 0):,.2f}")
    print(f"Equity: ${summary.get('starting_equity_usd', 0):,.2f} → ${summary.get('ending_equity_usd', 0):,.2f}")
    print(f"Simulated: {summary.get('simulated', 0)} / {summary.get('candidates', 0)} candidates")
    print(f"Wins: {summary.get('wins', 0)} | Losses: {summary.get('losses', 0)} | No fill: {summary.get('no_fill', 0)}")
    print(f"Report: reports/PAPER_PNL.md")

  sys.exit(0 if summary.get("ok") else 1)


if __name__ == "__main__":
  main()
