#!/usr/bin/env python3
"""Validate forum/social strategies via multi-AI executive consensus."""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from engine.social_strategy_validation import load_social_validation, run_social_strategy_validation


def main() -> None:
  p = argparse.ArgumentParser(description="Social strategy executive validation")
  p.add_argument("--symbol", default="", help="Optional symbol context e.g. BTC/USDT")
  p.add_argument("--direction", default="", help="Optional LONG/SHORT context")
  p.add_argument("--refresh", action="store_true", help="Re-run validation")
  p.add_argument("--llm", action="store_true", help="Use multi-AI brain consensus (requires API keys)")
  args = p.parse_args()

  if args.refresh:
    report = run_social_strategy_validation(
      symbol=args.symbol,
      direction=args.direction,
      use_llm=args.llm,
    )
  else:
    report = load_social_validation() or run_social_strategy_validation(
      symbol=args.symbol,
      direction=args.direction,
      use_llm=args.llm,
    )
  print(json.dumps(report, indent=2, default=str))


if __name__ == "__main__":
  main()
