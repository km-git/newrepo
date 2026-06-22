#!/usr/bin/env python3
"""
Autodream monitor daemon — re-scan monitor_queue.json on a schedule.

Upgrades monitor → executable when triggers hit:
  - Style TF impulse passes R1/R2/R3 (direction-aligned)
  - Price enters entry zone
  - Rejection wick on last bar

Downgrades or removes on invalidation:
  - 1d close beyond stop
  - Impulse flips opposite direction
"""

from __future__ import annotations

import argparse
import signal
import sys
import time
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from engine.autodream_monitor import DEFAULT_QUEUE_PATH, run_monitor_cycle


def _print_summary(summary: dict) -> None:
  print(
    f"[monitor] scanned={summary['scanned']} upgraded={summary['upgraded']} "
    f"downgraded={summary['downgraded']} invalidated={summary['invalidated']} "
    f"queue={summary.get('queue_size', 0)}"
  )
  for e in summary.get("events", []):
    if e.get("upgrade_note"):
      print(f"  ↑ {e['symbol']} {e['style']}: {e['upgrade_note']}")
    elif e.get("new_status") == "invalidated":
      reasons = "; ".join(e.get("invalidate_reasons") or [])
      print(f"  ✗ {e['symbol']} {e['style']}: INVALIDATED — {reasons}")
    elif e.get("triggers_hit"):
      print(
        f"  · {e['symbol']} {e['style']}: {e.get('new_status')} "
        f"({', '.join(e['triggers_hit'][:2])})"
      )


def main() -> None:
  p = argparse.ArgumentParser(description="Autodream monitor — upgrade setups on trigger")
  p.add_argument("--queue", default=str(DEFAULT_QUEUE_PATH), help="Path to monitor_queue.json")
  p.add_argument("--interval", type=int, default=300, help="Seconds between scans (daemon mode)")
  p.add_argument("--once", action="store_true", help="Run one scan and exit")
  p.add_argument("--daemon", action="store_true", help="Loop forever with --interval")
  p.add_argument("--crypto", action="store_true", default=True, help="Fetch via ccxt (default)")
  p.add_argument("--no-crypto", action="store_true", help="Use yfinance instead of ccxt")
  args = p.parse_args()

  is_crypto = not args.no_crypto
  stop = False

  def _handle_sig(sig, frame):
    nonlocal stop
    stop = True
    print("\n[monitor] shutdown requested", file=sys.stderr)

  signal.signal(signal.SIGINT, _handle_sig)
  signal.signal(signal.SIGTERM, _handle_sig)

  def cycle() -> None:
    summary = run_monitor_cycle(queue_path=args.queue, is_crypto=is_crypto)
    _print_summary(summary)

  if args.once or not args.daemon:
    cycle()
    return

  print(f"[monitor] daemon started interval={args.interval}s queue={args.queue}", file=sys.stderr)
  while not stop:
    t0 = time.time()
    try:
      cycle()
    except Exception as exc:
      print(f"[monitor] error: {exc}", file=sys.stderr)
    elapsed = time.time() - t0
    sleep_for = max(1, args.interval - elapsed)
    for _ in range(int(sleep_for)):
      if stop:
        break
      time.sleep(1)
  print("[monitor] stopped", file=sys.stderr)


if __name__ == "__main__":
  main()
