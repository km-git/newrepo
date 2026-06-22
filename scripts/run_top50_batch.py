#!/usr/bin/env python3
"""Run EW analysis on top N crypto pairs across all timeframes."""

from __future__ import annotations

import argparse
import sys
import time

from engine.top50_batch import DEFAULT_TFS, run_top_crypto_batch


def main() -> None:
  p = argparse.ArgumentParser(description="Batch EW analysis for top crypto pairs")
  p.add_argument("-n", "--count", type=int, default=50, help="Number of pairs (default 50)")
  p.add_argument("--tfs", default=",".join(DEFAULT_TFS), help="Comma-separated timeframes")
  p.add_argument("--quote", default="USDT", help="Quote currency")
  p.add_argument("--output-dir", default="output", help="Output directory")
  args = p.parse_args()

  tfs = [t.strip() for t in args.tfs.split(",")]
  t0 = time.time()
  meta = run_top_crypto_batch(
    n=args.count,
    tfs=tfs,
    output_dir=args.output_dir,
    quote=args.quote,
  )
  elapsed = time.time() - t0
  print(f"\n[done] {meta['pairs_count']} pairs in {elapsed:.0f}s ({elapsed/60:.1f} min)", file=sys.stderr)


if __name__ == "__main__":
  main()
