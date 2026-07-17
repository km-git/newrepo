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
  parser.add_argument("--top", type=int, default=None, help="Run top N crypto USDT pairs (e.g. 50)")
  parser.add_argument("--quote", default="USDT", help="Quote for --top (default USDT)")
  parser.add_argument("--output-dir", default="output", help="Output dir for --top batch")
  parser.add_argument("--outcomes-only", action="store_true", help="Print step8 outcomes JSON only")
  parser.add_argument("--cache-stats", action="store_true", help="Print cache stats after run")
  parser.add_argument("--clear-cache", action="store_true", help="Clear cache before run")
  parser.add_argument("--gateway-stats", action="store_true", help="Print semantic gateway cache stats")
  parser.add_argument(
    "--llm-advisory",
    action="store_true",
    help="Consult Claude + GPT on critical decisions (GO/CONDITIONAL_GO/executable); needs API keys",
  )
  parser.add_argument("--repomix", action="store_true", help="Export RepoMix-style code pack and exit")
  parser.add_argument("--repomix-out", default="output/repomix_pack.xml", help="RepoMix output path")
  args = parser.parse_args()

  if args.repomix:
    from gateway.repomix_export import pack_repository

    packed = pack_repository(".")
    import os
    os.makedirs(os.path.dirname(args.repomix_out) or ".", exist_ok=True)
    with open(args.repomix_out, "w") as f:
      f.write(packed)
    print(f"[repomix] wrote {args.repomix_out} ({len(packed):,} chars)")
    return

  if args.clear_cache:
    from cache.disk_cache import get_cache

    import shutil

    cache_dir = get_cache().cache_dir
    if cache_dir.exists():
      shutil.rmtree(cache_dir)
      print(f"[cache] cleared {cache_dir}")

  tfs = [t.strip() for t in args.tfs.split(",")]
  t0 = time.time()

  if args.batch or args.top:
    if args.top:
      from engine.top50_batch import run_top_crypto_batch

      meta = run_top_crypto_batch(
        n=args.top,
        tfs=tfs,
        output_dir=args.output_dir,
        quote=args.quote,
        llm_advisory=args.llm_advisory,
      )
      if args.save:
        import shutil
        shutil.copy(meta["json"], args.save)
      elapsed = time.time() - t0
      print(f"\n[done] top {args.top} batch in {elapsed:.0f}s", file=sys.stderr)
      if args.cache_stats:
        from cache.disk_cache import get_cache
        print(f"[cache] {get_cache().stats()}", file=sys.stderr)
    else:
      results = run_batch(args.batch, tfs, args.crypto, llm_advisory=args.llm_advisory)
      if args.save:
        save_batch_json(results, args.save)
      else:
        print(json.dumps(results, indent=2, default=str))
  else:
    if not args.symbol:
      parser.error("--symbol is required unless --batch is used")
    result = adaptive_pipeline(args.symbol, tfs, args.crypto, llm_advisory=args.llm_advisory)
    validated = ElliottWaveOutput(**result)
    payload = validated.model_dump()
    elapsed = time.time() - t0
    print(f"\n[done] {args.symbol} status={validated.status} elapsed={elapsed:.1f}s", file=sys.stderr)
    if args.cache_stats and validated.cache_stats:
      print(f"[cache] {validated.cache_stats}", file=sys.stderr)
    if args.gateway_stats and args.crypto:
      from gateway.market_gateway import get_gateway
      print(f"[gateway] {get_gateway().stats()}", file=sys.stderr)
    if args.save:
      with open(args.save, "w") as f:
        json.dump(payload, f, indent=2, default=str)
    elif args.outcomes_only:
      print(json.dumps(payload.get("step8_outcomes", {}), indent=2, default=str))
    else:
      print(json.dumps(payload, indent=2, default=str))


if __name__ == "__main__":
  main()
