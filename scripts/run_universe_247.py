#!/usr/bin/env python3
"""24/7 universe scanner — rotate through 1000 pairs × all timeframes."""

from __future__ import annotations

import argparse
import os
import sys
import time
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from engine.autodream_monitor import run_monitor_cycle
from engine.timeframes import UNIVERSE_TFS
from engine.universe_scanner import run_universe_tick


def main() -> None:
  p = argparse.ArgumentParser(description="24/7 universe scanner for top crypto pairs")
  p.add_argument("--size", type=int, default=int(os.environ.get("UNIVERSE_SIZE", "1000")))
  p.add_argument("--chunk", type=int, default=int(os.environ.get("CHUNK_SIZE", "25")))
  p.add_argument("--interval", type=int, default=int(os.environ.get("TICK_INTERVAL", "300")),
                 help="Seconds between ticks (default 300)")
  p.add_argument("--paper-max", type=int, default=int(os.environ.get("UNIVERSE_PAPER_MAX", "150")))
  p.add_argument("--quote", default=os.environ.get("QUOTE", "USDT"))
  p.add_argument("--output-dir", default="output")
  p.add_argument("--tfs", default=",".join(UNIVERSE_TFS))
  p.add_argument("--once", action="store_true", help="Run one tick and exit")
  p.add_argument("--refresh-pairs", action="store_true", help="Force refresh pair list")
  p.add_argument("--skip-monitor", action="store_true")
  p.add_argument("--llm-advisory", action="store_true",
                 default=os.environ.get("EW_LLM_ADVISORY", "").lower() in ("1", "true", "yes"))
  p.add_argument("--llm-max", type=int, default=int(os.environ.get("EW_UNIVERSE_LLM_MAX", "3")))
  args = p.parse_args()

  tfs = [t.strip() for t in args.tfs.split(",") if t.strip()]

  while True:
    t0 = time.time()
    try:
      result = run_universe_tick(
        universe_size=args.size,
        chunk_size=args.chunk,
        tfs=tfs,
        output_dir=args.output_dir,
        quote=args.quote,
        paper_max=args.paper_max,
        refresh_pairs=args.refresh_pairs,
        llm_advisory=args.llm_advisory,
        llm_advisory_max=args.llm_max,
      )
      print(
        f"\n[universe] Tick done — chunk {result['chunk_index'] + 1}/{result['n_chunks']}, "
        f"store={result['symbols_in_store']}, finalized={result['finalized']}",
        file=sys.stderr,
      )
      if result.get("finalize"):
        fin = result["finalize"]
        print(
          f"  Board: {fin.get('board_picks')} picks → {fin.get('best_trades_csv')}",
          file=sys.stderr,
        )

      if not args.skip_monitor:
        monitor = run_monitor_cycle(
          queue_path=Path(args.output_dir) / "autodream" / "monitor_queue.json",
          is_crypto=True,
        )
        print(
          f"  Monitor: scanned={monitor.get('scanned')} upgraded={monitor.get('upgraded')}",
          file=sys.stderr,
        )
    except Exception as e:
      print(f"[universe] ERROR: {e}", file=sys.stderr)
      import traceback
      traceback.print_exc()

    elapsed = time.time() - t0
    if args.once:
      break
    sleep_for = max(10, args.interval - int(elapsed))
    print(f"[universe] Sleeping {sleep_for}s until next tick...", file=sys.stderr)
    time.sleep(sleep_for)


if __name__ == "__main__":
  main()
