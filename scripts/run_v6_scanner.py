#!/usr/bin/env python3
"""One-shot V6 scanner: chunk or full universe with best-trade export."""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))


def main() -> None:
  p = argparse.ArgumentParser(description="V6 multi-TF scanner (15m–1w incl 12h)")
  p.add_argument("--full", action="store_true", help="Scan full universe (slow)")
  p.add_argument("--chunk", action="store_true", help="Scan next chunk only (default)")
  p.add_argument("--pairs", type=int, default=None, help="Target universe size (default EW_SCANNER_PAIRS or 1000)")
  p.add_argument("--chunk-size", type=int, default=None, help="Pairs per chunk scan")
  p.add_argument("--no-swap", action="store_true", help="Spot USDT only")
  args = p.parse_args()

  from engine.monetize import AccessController
  from engine.v6_scanner import run_v6_chunk_scan, run_v6_full_batch

  try:
    AccessController().require("v6_scanner")
  except AccessController.AccessDeniedError as exc:
    print(f"[monetize] {exc}", file=sys.stderr)
    print(
      "[monetize] Upgrade via EW_LICENSE_TIER=enterprise. See --monetize-status.",
      file=sys.stderr,
    )
    sys.exit(2)

  if args.full:
    result = run_v6_full_batch(n=args.pairs, include_swap=not args.no_swap)
  else:
    result = run_v6_chunk_scan(
      chunk_size=args.chunk_size,
      include_swap=not args.no_swap,
      force_full=False,
    )
  print(json.dumps(result, indent=2, default=str))


if __name__ == "__main__":
  main()
