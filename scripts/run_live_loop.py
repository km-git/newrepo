#!/usr/bin/env python3
"""Run the live trading loop — monitor tick + execution drain + optional batch."""

from __future__ import annotations

import argparse
import json

from engine.live_loop import run_live_loop, run_live_tick


def main() -> None:
  p = argparse.ArgumentParser(description="Live monitor + execution loop")
  p.add_argument("--batch-n", type=int, default=50, help="Top-N pairs for batch refresh")
  p.add_argument("--batch-interval", type=int, default=3600, help="Batch interval seconds")
  p.add_argument("--force-batch", action="store_true", help="Force full batch on this tick")
  p.add_argument("--tick-only", action="store_true", help="Monitor + execute only, no batch")
  p.add_argument("--max-executions", type=int, default=3, help="Max paper executions per tick")
  p.add_argument("--no-execute", action="store_true", help="Skip execution drain")
  p.add_argument("--output-dir", default="output")
  args = p.parse_args()

  if args.tick_only:
    result = run_live_tick(
      monitor=True,
      execute=not args.no_execute,
      rebuild_queue=True,
      max_executions=args.max_executions,
      queue_path=f"{args.output_dir}/autodream/monitor_queue.json",
    )
  else:
    result = run_live_loop(
      batch_n=args.batch_n,
      batch_interval_sec=args.batch_interval,
      output_dir=args.output_dir,
      force_batch=args.force_batch,
      max_executions_per_tick=args.max_executions,
    )

  print(json.dumps(result, indent=2, default=str))


if __name__ == "__main__":
  main()
