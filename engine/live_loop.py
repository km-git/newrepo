"""Live trading loop — monitor tick, execution drain, periodic batch."""

from __future__ import annotations

import json
import sys
import time
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, Optional

from engine.autodream_monitor import DEFAULT_QUEUE_PATH, run_monitor_cycle
from engine.autodream_scheduler import (
  batch_is_due,
  load_state,
  run_batch_refresh,
  save_state,
)
from engine.execution_adapter import drain_execution_queue
from engine.execution_queue import (
  QUEUE_PATH,
  build_execution_queue,
  collect_monitor_upgrades_from_events,
  load_execution_queue,
  save_execution_queue,
)
from engine.executive_board import BOARD_PATH

STATE_PATH = Path("output/autodream/live_loop_state.json")


def load_live_state(path: Path = STATE_PATH) -> dict:
  if not path.exists():
    return {}
  try:
    return json.loads(path.read_text())
  except (json.JSONDecodeError, OSError):
    return {}


def save_live_state(state: dict, path: Path = STATE_PATH) -> None:
  path.parent.mkdir(parents=True, exist_ok=True)
  path.write_text(json.dumps(state, indent=2, default=str))


def _load_board() -> dict:
  if not BOARD_PATH.exists():
    return {"picks": []}
  return json.loads(BOARD_PATH.read_text())


def run_live_tick(
  *,
  monitor: bool = True,
  execute: bool = True,
  rebuild_queue: bool = True,
  max_executions: int = 3,
  queue_path: str | Path = DEFAULT_QUEUE_PATH,
  is_crypto: bool = True,
  dry_run: bool = False,
) -> Dict[str, Any]:
  """
  One live tick:
  1. Monitor scan (EW + SMC)
  2. Rebuild execution queue from board + upgrades
  3. Drain approved paper executions (or dry-run preview)
  """
  result: Dict[str, Any] = {
    "ts": datetime.now(timezone.utc).isoformat(),
    "monitor": None,
    "execution_queue": None,
    "execution": None,
    "dry_run": dry_run,
  }

  monitor_summary = None
  queue_doc: dict = {"queue": []}
  if monitor:
    monitor_summary = run_monitor_cycle(queue_path=queue_path, is_crypto=is_crypto)
    result["monitor"] = monitor_summary
    if Path(queue_path).exists():
      queue_doc = json.loads(Path(queue_path).read_text())

  upgraded = []
  if monitor_summary:
    upgraded = collect_monitor_upgrades_from_events(
      monitor_summary.get("events", []),
      queue_doc.get("queue", []),
    )

  if rebuild_queue:
    board = _load_board()
    eq = build_execution_queue(board=board, monitor_queue=upgraded, approve=True)
    save_execution_queue(eq)
    result["execution_queue"] = {
      "approved_count": eq.get("approved_count"),
      "rejected_count": eq.get("rejected_count"),
      "upgrade_count": len(upgraded),
      "path": str(QUEUE_PATH),
    }
  else:
    eq = load_execution_queue()

  if execute and eq.get("approved"):
    drain = drain_execution_queue(
      eq, mode="paper", max_trades=max_executions, dry_run=dry_run,
    )
    result["execution"] = drain

  state = load_live_state()
  state["last_tick_utc"] = result["ts"]
  state["last_monitor"] = monitor_summary
  state["last_execution"] = result.get("execution")
  state["last_dry_run"] = dry_run
  save_live_state(state)
  return result


def run_live_loop(
  *,
  batch_n: int = 50,
  batch_interval_sec: int = 3600,
  output_dir: str = "output",
  force_batch: bool = False,
  skip_batch: bool = False,
  skip_monitor: bool = False,
  execute: bool = True,
  max_executions_per_tick: int = 3,
  is_crypto: bool = True,
  dry_run: bool = False,
) -> dict:
  """
  Combined scheduler tick: optional hourly batch + monitor/execution tick.
  Monitor runs every call unless skipped; batch only when due.
  """
  sched_state = load_state()
  result: Dict[str, Any] = {
    "batch_ran": False,
    "batch": None,
    "live_tick": None,
    "dry_run": dry_run,
  }

  queue_path = Path(output_dir) / "autodream" / "monitor_queue.json"
  if not skip_batch and (force_batch or batch_is_due(sched_state, batch_interval_sec, queue_path)):
    print(f"[live_loop] running top-{batch_n} batch refresh")
    meta = run_batch_refresh(n=batch_n, output_dir=output_dir)
    sched_state["last_batch_utc"] = datetime.now(timezone.utc).isoformat()
    sched_state["latest"] = meta.get("latest")
    result["batch_ran"] = True
    result["batch"] = meta

  if not skip_monitor:
    tick = run_live_tick(
      monitor=True,
      execute=execute,
      rebuild_queue=True,
      max_executions=max_executions_per_tick,
      queue_path=queue_path,
      is_crypto=is_crypto,
      dry_run=dry_run,
    )
    result["live_tick"] = tick
    sched_state["last_monitor_utc"] = tick["ts"]
  save_state(sched_state)
  return result


def print_batch_summary(meta: Optional[dict]) -> None:
  if not meta:
    return
  latest = meta.get("latest", {})
  print(
    f"[batch] {meta.get('pairs_count')} pairs · verdicts={meta.get('by_verdict')}"
  )
  if latest.get("full_html"):
    print(f"[batch] latest view → {latest['full_html']}")
  if meta.get("execution_approved") is not None:
    print(f"[batch] execution queue: {meta.get('execution_approved')} approved")


def print_monitor_summary(summary: Optional[dict]) -> None:
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


def print_execution_summary(execution: Optional[dict], dry_run: bool = False) -> None:
  if not execution:
    return
  label = "dry-run" if dry_run else "execution"
  print(
    f"[{label}] executed={execution.get('executed', 0)} "
    f"skipped={execution.get('skipped', 0)} "
    f"dedup_skipped={execution.get('dedup_skipped', 0)}"
  )
  for t in execution.get("trades", []):
    if dry_run:
      print(
        f"  → WOULD {t['symbol']} {t.get('style')} {t.get('direction')} "
        f"@ {t.get('calibrated_size_pct')}% ({t.get('source')})"
      )
    else:
      print(
        f"  → {t['symbol']} {t.get('style')} outcome={t.get('paper_outcome')} "
        f"pnl_r={t.get('paper_pnl_r')}"
      )


def print_tick_summary(result: dict) -> None:
  if result.get("batch_ran"):
    print_batch_summary(result.get("batch"))
  elif result.get("live_tick") is None and not result.get("batch_ran"):
    print("[live_loop] batch not due — monitor only")
  tick = result.get("live_tick") or result
  dry = result.get("dry_run") or tick.get("dry_run", False)
  print_monitor_summary(tick.get("monitor"))
  eq = tick.get("execution_queue")
  if eq:
    print(
      f"[queue] approved={eq.get('approved_count')} rejected={eq.get('rejected_count')} "
      f"upgrades={eq.get('upgrade_count', 0)}"
    )
  print_execution_summary(tick.get("execution"), dry_run=dry)


def run_daemon_loop(
  *,
  interval_sec: int = 300,
  batch_interval_sec: int = 3600,
  batch_n: int = 50,
  output_dir: str = "output",
  queue_path: str | Path = DEFAULT_QUEUE_PATH,
  is_crypto: bool = True,
  force_batch_first: bool = False,
  skip_batch: bool = False,
  skip_monitor: bool = False,
  max_executions: int = 3,
  dry_run: bool = False,
  execute: bool = True,
  stop_flag: Optional[list] = None,
) -> None:
  """Long-running daemon — tick every interval_sec until stop_flag[0] is True."""
  first = True
  while not (stop_flag and stop_flag[0]):
    t0 = time.time()
    try:
      if skip_batch and skip_monitor:
        print("[daemon] nothing to do — both batch and monitor skipped", file=sys.stderr)
        break
      result = run_live_loop(
        batch_n=batch_n,
        batch_interval_sec=0 if skip_batch else batch_interval_sec,
        output_dir=output_dir,
        force_batch=force_batch_first and first and not skip_batch,
        skip_batch=skip_batch,
        skip_monitor=skip_monitor,
        max_executions_per_tick=max_executions,
        is_crypto=is_crypto,
        dry_run=dry_run,
        execute=execute,
      )
      print_tick_summary(result)
    except Exception as exc:
      print(f"[daemon] error: {exc}", file=sys.stderr)
    first = False
    elapsed = time.time() - t0
    sleep_for = max(1, interval_sec - elapsed)
    for _ in range(int(sleep_for)):
      if stop_flag and stop_flag[0]:
        break
      time.sleep(1)
