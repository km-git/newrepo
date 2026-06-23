#!/usr/bin/env python3
"""
Live trading daemon — monitor + execution queue + optional hourly batch.

Examples:
  # Dry-run daemon (log only, no paper trades)
  PYTHONPATH=/workspace python3 scripts/run_live_loop.py --daemon --dry-run --interval 300

  # Live paper execution every 5 min, batch every hour
  PYTHONPATH=/workspace python3 scripts/run_live_loop.py --daemon --interval 300 --batch-interval 3600

  # Single tick with dry-run
  PYTHONPATH=/workspace python3 scripts/run_live_loop.py --tick-only --dry-run
"""

from __future__ import annotations

import argparse
import json
import signal
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from engine.autodream_monitor import DEFAULT_QUEUE_PATH
from engine.live_loop import (
  print_tick_summary,
  run_daemon_loop,
  run_live_loop,
  run_live_tick,
)


def main() -> None:
  p = argparse.ArgumentParser(description="Live monitor + execution daemon")
  p.add_argument("--queue", default=str(DEFAULT_QUEUE_PATH))
  p.add_argument("--batch-n", type=int, default=50, help="Top-N pairs for batch refresh")
  p.add_argument("--batch-interval", type=int, default=3600, help="Batch interval seconds (0=disable)")
  p.add_argument("--interval", type=int, default=300, help="Seconds between daemon ticks")
  p.add_argument("--force-batch", action="store_true", help="Force full batch on first tick")
  p.add_argument("--batch-now", action="store_true", help="Alias for --force-batch")
  p.add_argument("--tick-only", action="store_true", help="Single monitor+execute tick, no batch")
  p.add_argument("--once", action="store_true", help="Single tick then exit (alias for --tick-only with daemon off)")
  p.add_argument("--daemon", action="store_true", help="Loop with --interval")
  p.add_argument("--batch-only", action="store_true", help="Batch only, skip monitor/execute")
  p.add_argument("--monitor-only", action="store_true", help="Monitor only, skip batch")
  p.add_argument("--max-executions", type=int, default=3, help="Max executions per tick")
  p.add_argument("--no-execute", action="store_true", help="Skip execution drain")
  p.add_argument("--dry-run", action="store_true", help="Log would-execute trades, no ledger writes")
  p.add_argument("--json", action="store_true", help="Emit JSON summary instead of human output")
  p.add_argument("--output-dir", default="output")
  p.add_argument("--no-crypto", action="store_true")
  args = p.parse_args()

  is_crypto = not args.no_crypto
  force_batch = args.force_batch or args.batch_now
  dry_run = args.dry_run
  once = args.once or args.tick_only

  if args.daemon and once:
    print("error: --daemon and --tick-only/--once are mutually exclusive", file=sys.stderr)
    sys.exit(1)

  stop_flag = [False]

  def _handle_sig(sig, frame):
    stop_flag[0] = True
    print("\n[daemon] shutdown requested", file=sys.stderr)

  signal.signal(signal.SIGINT, _handle_sig)
  signal.signal(signal.SIGTERM, _handle_sig)

  if args.daemon:
    print(
      f"[daemon] live loop started tick={args.interval}s batch_interval={args.batch_interval}s "
      f"dry_run={dry_run} max_executions={args.max_executions}",
      file=sys.stderr,
    )
    run_daemon_loop(
      interval_sec=args.interval,
      batch_interval_sec=args.batch_interval,
      batch_n=args.batch_n,
      output_dir=args.output_dir,
      queue_path=args.queue,
      is_crypto=is_crypto,
      force_batch_first=force_batch,
      skip_batch=args.monitor_only,
      skip_monitor=args.batch_only,
      max_executions=args.max_executions,
      dry_run=dry_run,
      execute=not args.no_execute,
      stop_flag=stop_flag,
    )
    print("[daemon] stopped", file=sys.stderr)
    return

  if once:
    result = run_live_tick(
      monitor=not args.batch_only,
      execute=not args.no_execute,
      rebuild_queue=True,
      max_executions=args.max_executions,
      queue_path=args.queue,
      is_crypto=is_crypto,
      dry_run=dry_run,
    )
    if args.json:
      print(json.dumps(result, indent=2, default=str))
    else:
      print_tick_summary({"live_tick": result, "dry_run": dry_run})
    return

  result = run_live_loop(
    batch_n=args.batch_n,
    batch_interval_sec=0 if args.monitor_only else args.batch_interval,
    output_dir=args.output_dir,
    force_batch=force_batch,
    skip_batch=args.monitor_only,
    skip_monitor=args.batch_only,
    max_executions_per_tick=args.max_executions,
    is_crypto=is_crypto,
    dry_run=dry_run,
    execute=not args.no_execute,
  )
  if args.json:
    print(json.dumps(result, indent=2, default=str))
  else:
    print_tick_summary(result)


if __name__ == "__main__":
  main()
