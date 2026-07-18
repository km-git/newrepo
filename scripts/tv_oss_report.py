#!/usr/bin/env python3
"""TV OSS complementary stack report — explore, discover, and executive consensus."""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from engine.tv_oss_consensus import load_tv_oss_consensus, run_tv_oss_consensus
from engine.tv_oss_discovery import load_tv_oss_discovery, run_tv_oss_discovery


def main() -> None:
  p = argparse.ArgumentParser(description="TV OSS executive consensus report")
  p.add_argument("--refresh", action="store_true", help="Re-run consensus")
  p.add_argument("--explore", action="store_true", help="Run dynamic discovery only")
  p.add_argument("--llm", action="store_true", help="Multi-AI brain panel fine-tune")
  args = p.parse_args()

  if args.explore:
    report = run_tv_oss_discovery(use_llm=args.llm)
  elif args.refresh:
    report = run_tv_oss_consensus(use_llm=args.llm)
  else:
    report = load_tv_oss_consensus() or load_tv_oss_discovery() or run_tv_oss_consensus(use_llm=args.llm)
  print(json.dumps(report, indent=2, default=str))


if __name__ == "__main__":
  main()
