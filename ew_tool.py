#!/usr/bin/env python3
"""Elliott Wave + Harmonic confluence trading analysis CLI."""

from __future__ import annotations

import argparse
import json
import sys
import time

from engine.adaptive import adaptive_pipeline
from engine.batch import run_batch, save_batch_json
from schemas.models import ElliottWaveOutput


def main() -> None:
  parser = argparse.ArgumentParser(description="Elliott Wave + Harmonic confluence tool")
  parser.add_argument("--symbol", help="e.g., BTC/USDT, ES=F, EURUSD=X")
  parser.add_argument("--tfs", default="1w,1d,4h,1h,15m", help="Comma-separated timeframes")
  parser.add_argument("--crypto", action="store_true", help="Use ccxt instead of yfinance")
  parser.add_argument("--save", default=None, help="Path to save JSON output")
  parser.add_argument("--batch", default=None, help="Path to CSV with symbols for batch run")
  parser.add_argument("--cache-stats", action="store_true", help="Print cache stats after run")
  parser.add_argument("--clear-cache", action="store_true", help="Clear cache before run")
  args = parser.parse_args()

  if args.clear_cache:
    from cache.disk_cache import get_cache

    import shutil

    cache_dir = get_cache().cache_dir
    if cache_dir.exists():
      shutil.rmtree(cache_dir)
      print(f"[cache] cleared {cache_dir}")

  tfs = [t.strip() for t in args.tfs.split(",")]
  t0 = time.time()

  if args.batch:
    results = run_batch(args.batch, tfs, args.crypto)
    output = json.dumps(results, indent=2, default=str)
    if args.save:
      save_batch_json(results, args.save)
    else:
      print(output)
  else:
    if not args.symbol:
      parser.error("--symbol is required unless --batch is used")
    result = adaptive_pipeline(args.symbol, tfs, args.crypto)
    validated = ElliottWaveOutput(**result)
    payload = validated.model_dump()
    elapsed = time.time() - t0
    print(f"\n[done] {args.symbol} status={validated.status} elapsed={elapsed:.1f}s", file=sys.stderr)
    if args.cache_stats and validated.cache_stats:
      print(f"[cache] {validated.cache_stats}", file=sys.stderr)
    if args.save:
      with open(args.save, "w") as f:
        json.dump(payload, f, indent=2, default=str)
    else:
      print(json.dumps(payload, indent=2, default=str))


if __name__ == "__main__":
  main()
