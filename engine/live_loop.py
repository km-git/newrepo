"""Live trading loop — monitor tick, execution drain, periodic batch."""

from __future__ import annotations

import json
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, Optional

from engine.autodream_monitor import DEFAULT_QUEUE_PATH, run_monitor_cycle
from engine.autodream_scheduler import (
  batch_is_due,
  load_state,
  publish_latest,
  run_batch_refresh,
  save_state,
)
from engine.execution_adapter import drain_execution_queue
from engine.execution_queue import (
  QUEUE_PATH,
  build_execution_queue,
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
) -> Dict[str, Any]:
  """
  One live tick:
  1. Monitor scan (EW + SMC)
  2. Rebuild execution queue from board + upgrades
  3. Drain approved paper executions
  """
  result: Dict[str, Any] = {
    "ts": datetime.now(timezone.utc).isoformat(),
    "monitor": None,
    "execution_queue": None,
    "execution": None,
  }

  monitor_summary = None
  upgraded_queue: list = []
  if monitor:
    monitor_summary = run_monitor_cycle(queue_path=queue_path, is_crypto=is_crypto)
    result["monitor"] = monitor_summary
    doc = json.loads(Path(queue_path).read_text()) if Path(queue_path).exists() else {}
    upgraded_queue = [
      item for item in doc.get("queue", [])
      if item.get("upgrade_note") or (
        item.get("prior_status") == "monitor" and item.get("new_status") == "executable"
      )
    ]

  if rebuild_queue:
    board = _load_board()
    eq = build_execution_queue(board=board, monitor_queue=upgraded_queue, approve=True)
    save_execution_queue(eq)
    result["execution_queue"] = {
      "approved_count": eq.get("approved_count"),
      "rejected_count": eq.get("rejected_count"),
      "path": str(QUEUE_PATH),
    }
  else:
    eq = load_execution_queue()

  if execute and eq.get("approved"):
    drain = drain_execution_queue(eq, mode="paper", max_trades=max_executions)
    result["execution"] = drain

  state = load_live_state()
  state["last_tick_utc"] = result["ts"]
  state["last_monitor"] = monitor_summary
  state["last_execution"] = result.get("execution")
  save_live_state(state)
  return result


def run_live_loop(
  *,
  batch_n: int = 50,
  batch_interval_sec: int = 3600,
  monitor_interval_sec: int = 300,
  output_dir: str = "output",
  force_batch: bool = False,
  max_executions_per_tick: int = 3,
  is_crypto: bool = True,
) -> dict:
  """
  Combined scheduler tick: optional hourly batch + monitor/execution tick.
  Monitor runs every call; batch only when due.
  """
  sched_state = load_state()
  result: Dict[str, Any] = {
    "batch_ran": False,
    "batch": None,
    "live_tick": None,
  }

  queue_path = Path(output_dir) / "autodream" / "monitor_queue.json"
  if force_batch or batch_is_due(sched_state, batch_interval_sec, queue_path):
    print(f"[live_loop] running top-{batch_n} batch refresh")
    meta = run_batch_refresh(n=batch_n, output_dir=output_dir)
    sched_state["last_batch_utc"] = datetime.now(timezone.utc).isoformat()
    sched_state["latest"] = meta.get("latest")
    result["batch_ran"] = True
    result["batch"] = meta

  tick = run_live_tick(
    monitor=True,
    execute=True,
    rebuild_queue=True,
    max_executions=max_executions_per_tick,
    queue_path=queue_path,
    is_crypto=is_crypto,
  )
  result["live_tick"] = tick
  sched_state["last_monitor_utc"] = tick["ts"]
  save_state(sched_state)
  return result
