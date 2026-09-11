#!/usr/bin/env python3
"""Evaluate autoresearch env proposals on cached batch analysis (no live promote)."""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from engine.autoresearch import run_autoresearch_eval_loop, latest_experiments_summary


def main() -> None:
  parser = argparse.ArgumentParser(description="AutoResearch eval loop on cached analysis")
  parser.add_argument("--analysis", default=None, help="Path to topN_analysis_*.json (default: newest in output/)")
  parser.add_argument("--max", type=int, default=None, help="Max experiments (default EW_AUTORESEARCH_MAX)")
  parser.add_argument("--no-baseline", action="store_true", help="Skip baseline_eval row")
  parser.add_argument("--summary", action="store_true", help="Print log summary only")
  args = parser.parse_args()

  if args.summary:
    print(json.dumps(latest_experiments_summary(), indent=2, default=str))
    return

  result = run_autoresearch_eval_loop(
    max_experiments=args.max,
    analysis_path=args.analysis,
    include_baseline=not args.no_baseline,
  )
  print(json.dumps(result, indent=2, default=str))
  sys.exit(0 if result.get("ok") else 1)


if __name__ == "__main__":
  main()
