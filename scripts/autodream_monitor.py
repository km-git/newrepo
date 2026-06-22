#!/usr/bin/env python3
"""
Autodream daemon — monitor queue + periodic full analysis refresh.

Each tick:
  1. Full top-N batch (if --batch-interval elapsed) → refreshes latest_analysis.html
  2. Monitor queue scan → upgrades monitor→executable on triggers

Examples:
  # Monitor only every 5 min (no batch)
  python3 scripts/autodream_monitor.py --daemon --interval 300 --batch-interval 0

  # Monitor every 5 min + full batch every 1 hour
  python3 scripts/autodream_monitor.py --daemon --interval 300 --batch-interval 3600

  # Start with immediate full batch, then loop
  python3 scripts/autodream_monitor.py --daemon --batch-now --batch-interval 3600
"""

from __future__ import annotations

import argparse
import signal
import sys
import time
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from engine.autodream_monitor import DEFAULT_QUEUE_PATH
from engine.autodream_scheduler import run_scheduler_cycle


def _print_batch(meta: dict | None) -> None:
  if not meta:
    return
  latest = meta.get("latest", {})
  print(
    f"[batch] {meta.get('pairs_count')} pairs · "
    f"verdicts={meta.get('by_verdict')}"
  )
  if latest.get("full_html"):
    print(f"[batch] latest view → {latest['full_html']}")


def _print_monitor(summary: dict | None) -> None:
  if not summary:
    return
  print(
    f"[monitor] scanned={summary.get('scanned', 0)} upgraded={summary.get('upgraded', 0)} "
    f"downgraded={summary.get('downgraded', 0)} invalidated={summary.get('invalidated', 0)} "
    f"queue={summary.get('queue_size', 0)}"
  )
  for e in summary.get("events", []):
    if e.get("upgrade_note"):
      print(f"  ↑ {e['symbol']} {e['style']}: {e['upgrade_note']}")
    elif e.get("new_status") == "invalidated":
      reasons = "; ".join(e.get("invalidate_reasons") or [])
      print(f"  ✗ {e['symbol']} {e['style']}: INVALIDATED — {reasons}")


def main() -> None:
  p = argparse.ArgumentParser(description="Autodream daemon — batch refresh + monitor")
  p.add_argument("--queue", default=str(DEFAULT_QUEUE_PATH))
  p.add_argument("--interval", type=int, default=300, help="Seconds between scheduler ticks")
  p.add_argument("--batch-interval", type=int, default=3600,
                 help="Seconds between full top-N batch runs (0=disable)")
  p.add_argument("--batch-n", type=int, default=50, help="Pairs for batch refresh")
  p.add_argument("--output-dir", default="output")
  p.add_argument("--quote", default="USDT")
  p.add_argument("--batch-now", action="store_true", help="Force full batch on first tick")
  p.add_argument("--batch-only", action="store_true", help="Run batch only, skip monitor")
  p.add_argument("--monitor-only", action="store_true", help="Run monitor only, skip batch")
  p.add_argument("--once", action="store_true", help="Single tick then exit")
  p.add_argument("--daemon", action="store_true", help="Loop with --interval")
  p.add_argument("--no-crypto", action="store_true")
  args = p.parse_args()

  is_crypto = not args.no_crypto
  batch_interval = 0 if args.monitor_only else args.batch_interval
  force_batch = args.batch_now and not args.monitor_only
  skip_monitor = args.batch_only

  stop = False
  first_tick = True

  def _handle_sig(sig, frame):
    nonlocal stop
    stop = True
    print("\n[daemon] shutdown requested", file=sys.stderr)

  signal.signal(signal.SIGINT, _handle_sig)
  signal.signal(signal.SIGTERM, _handle_sig)

  def tick() -> None:
    nonlocal first_tick
    do_batch = force_batch and first_tick
    first_tick = False
    out = run_scheduler_cycle(
      batch_n=args.batch_n,
      batch_interval_sec=batch_interval,
      output_dir=args.output_dir,
      quote=args.quote,
      queue_path=args.queue,
      is_crypto=is_crypto,
      force_batch=do_batch,
      skip_monitor=skip_monitor,
    )
    if out["batch_ran"]:
      _print_batch(out.get("batch"))
    elif batch_interval > 0:
      print("[scheduler] batch not due — monitor only")
    _print_monitor(out.get("monitor"))

  if args.once or not args.daemon:
    tick()
    return

  print(
    f"[daemon] started tick={args.interval}s batch_interval={batch_interval}s "
    f"batch_n={args.batch_n} batch_now={args.batch_now}",
    file=sys.stderr,
  )
  while not stop:
    t0 = time.time()
    try:
      tick()
    except Exception as exc:
      print(f"[daemon] error: {exc}", file=sys.stderr)
    elapsed = time.time() - t0
    sleep_for = max(1, args.interval - elapsed)
    for _ in range(int(sleep_for)):
      if stop:
        break
      time.sleep(1)
  print("[daemon] stopped", file=sys.stderr)


if __name__ == "__main__":
  main()
