#!/usr/bin/env python3
"""Print live dry-run / daemon status for validation."""

from __future__ import annotations

import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

LOG = ROOT / "output/autodream/logs/live_dry_run.log"
STATE = ROOT / "output/autodream/live_loop_state.json"
QUEUE = ROOT / "output/autodream/execution_queue.json"
EXEC_LOG = ROOT / "output/autodream/execution_log.jsonl"
MONITOR_Q = ROOT / "output/autodream/monitor_queue.json"


def _load_json(path: Path) -> dict:
  if not path.exists():
    return {}
  try:
    return json.loads(path.read_text())
  except (json.JSONDecodeError, OSError):
    return {}


def _tail_lines(path: Path, n: int = 15) -> list[str]:
  if not path.exists():
    return []
  lines = path.read_text(errors="replace").splitlines()
  return lines[-n:]


def _recent_dry_run_events(n: int = 10) -> list[dict]:
  if not EXEC_LOG.exists():
    return []
  events = []
  for line in EXEC_LOG.read_text().splitlines():
    line = line.strip()
    if not line:
      continue
    try:
      e = json.loads(line)
    except json.JSONDecodeError:
      continue
    if e.get("mode") in ("dry_run", "dedup"):
      events.append(e)
  return events[-n:]


def main() -> None:
  print("=== Live Dry-Run Status ===\n")

  state = _load_json(STATE)
  if state:
    print(f"Last tick:  {state.get('last_tick_utc', 'n/a')}")
    print(f"Dry-run:    {state.get('last_dry_run', 'n/a')}")
    mon = state.get("last_monitor") or {}
    print(
      f"Monitor:    scanned={mon.get('scanned', 0)} upgraded={mon.get('upgraded', 0)} "
      f"invalidated={mon.get('invalidated', 0)} queue={mon.get('queue_size', 0)}"
    )
    ex = state.get("last_execution") or {}
    if ex:
      print(
        f"Execution:  executed={ex.get('executed', 0)} skipped={ex.get('skipped', 0)} "
        f"dedup_skipped={ex.get('dedup_skipped', 0)} dry_run={ex.get('dry_run')}"
      )
  else:
    print("No live_loop_state.json yet — first tick may still be running.\n")

  eq = _load_json(QUEUE)
  if eq:
    print(f"\nExecution queue ({eq.get('updated', 'n/a')}):")
    print(f"  Approved: {eq.get('approved_count', len(eq.get('approved', [])))}")
    print(f"  Rejected: {eq.get('rejected_count', len(eq.get('rejected', [])))}")
    for c in (eq.get("approved") or [])[:8]:
      print(
        f"  ✓ {c.get('symbol')} {c.get('style')} {c.get('direction')} "
        f"@ {c.get('calibrated_size_pct')}% ({c.get('source')})"
      )
    for c in (eq.get("rejected") or [])[:5]:
      print(f"  ✗ {c.get('symbol')}: {c.get('reject_reason', 'rejected')}")

  mq = _load_json(MONITOR_Q)
  if mq.get("queue"):
    smc = sum(1 for i in mq["queue"] if i.get("style") == "smc")
    print(f"\nMonitor queue: {len(mq['queue'])} items ({smc} SMC), updated {mq.get('updated')}")

  events = _recent_dry_run_events()
  if events:
    print(f"\nRecent dry-run / dedup events ({len(events)}):")
    for e in events[-8:]:
      print(f"  {e.get('ts', '')[:19]} {e.get('status')} {e.get('symbol')} {e.get('style', '')} {e.get('reason', '')}")

  summaries = [
    ln for ln in _tail_lines(LOG, 40)
    if ln.startswith("[batch]") or ln.startswith("[monitor]") or ln.startswith("[dry-run]")
    or ln.startswith("[queue]") or ln.startswith("[execution]")
  ]
  if summaries:
    print("\nLog summaries (recent):")
    for ln in summaries[-10:]:
      print(f"  {ln}")

  print(f"\nFull log: {LOG}")
  print("Attach daemon: tmux -f /exec-daemon/tmux.portal.conf attach-session -t live-dry-run-daemon")


if __name__ == "__main__":
  main()
