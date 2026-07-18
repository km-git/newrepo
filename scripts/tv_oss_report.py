#!/usr/bin/env python3
"""TV OSS complementary stack report — executive consensus on active indicators."""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from engine.tv_oss_consensus import load_tv_oss_consensus, run_tv_oss_consensus


def main() -> None:
  p = argparse.ArgumentParser(description="TV OSS executive consensus report")
  p.add_argument("--refresh", action="store_true", help="Re-run consensus")
  p.add_argument("--llm", action="store_true", help="Multi-AI brain panel")
  args = p.parse_args()

  report = (
    run_tv_oss_consensus(use_llm=args.llm)
    if args.refresh
    else (load_tv_oss_consensus() or run_tv_oss_consensus(use_llm=args.llm))
  )
  print(json.dumps(report, indent=2, default=str))


if __name__ == "__main__":
  main()
