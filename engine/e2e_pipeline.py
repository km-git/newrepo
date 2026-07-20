"""End-to-end trading analysis pipeline — analyze → learn → export → execute → improve."""

from __future__ import annotations

import csv
import json
import os
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, List, Optional

from engine.improvement_cycle import run_improvement_cycle
from engine.system_health import run_health_checks, save_health


E2E_STATE = Path(os.environ.get("EW_E2E_STATE", "output/system/e2e_state.json"))


def e2e_enabled() -> bool:
  return os.environ.get("EW_E2E_PIPELINE", "1").lower() not in ("0", "false", "no")


def _save_state(state: dict) -> None:
  E2E_STATE.parent.mkdir(parents=True, exist_ok=True)
  E2E_STATE.write_text(json.dumps(state, indent=2, default=str), encoding="utf-8")


def _load_export_rows(csv_path: str = "") -> List[dict]:
  p = Path(csv_path or os.environ.get("EW_LIMIT_ORDERS_CSV", "output/latest_limit_orders_all_tf.csv"))
  if not p.exists():
    return []
  return list(csv.DictReader(p.open(encoding="utf-8")))


def run_e2e_cycle(
  *,
  batch_n: int = 0,
  output_dir: str = "output",
  quote: str = "USDT",
  llm_advisory: bool = False,
  execute: bool = False,
  execute_live: bool = False,
  skip_batch: bool = False,
  skip_monitor: bool = False,
  force_batch: bool = False,
) -> Dict[str, Any]:
  """
  Full end-to-end cycle:

  1. **Learn** — resolve tracked setups, update metrics
  2. **Analyze** — top-N batch (optional) + monitor queue scan
  3. **Export** — limit orders (inside batch)
  4. **Execute** — paper/live on executable rows (optional)
  5. **Improve** — OKF lessons + health report
  """
  if not e2e_enabled():
    return {"ok": False, "error": "EW_E2E_PIPELINE disabled"}

  t0 = datetime.now(timezone.utc)
  result: Dict[str, Any] = {
    "ok": True,
    "started_at": t0.isoformat(),
    "phases": {},
  }

  # Phase 1: Learning (resolve prior setups before new analysis)
  print("[e2e] phase 1: learning — resolve tracked setups")
  learn = run_improvement_cycle(is_crypto=True, record_rows=None, persist_okf=True)
  result["phases"]["learn"] = {
    "resolved": learn.get("cycle", {}).get("resolved"),
    "win_rate": learn.get("cycle", {}).get("overall_win_rate"),
    "health": learn.get("health", {}).get("healthy"),
  }

  # Phase 2: Analysis + monitor
  batch_meta = None
  monitor = None
  if not skip_batch and (batch_n > 0 or force_batch):
    n = batch_n or int(os.environ.get("EW_E2E_BATCH_N", "50"))
    print(f"[e2e] phase 2: analyze — top-{n} batch")
    from engine.top50_batch import run_top_crypto_batch
    batch_meta = run_top_crypto_batch(
      n=n, output_dir=output_dir, quote=quote, llm_advisory=llm_advisory,
    )
    from engine.autodream_scheduler import publish_latest
    publish_latest(batch_meta, output_dir=output_dir)
    result["phases"]["batch"] = {
      "pairs": batch_meta.get("pairs_count"),
      "by_verdict": batch_meta.get("by_verdict"),
      "limit_csv": batch_meta.get("limit_orders_csv"),
    }
  elif not skip_monitor:
    print("[e2e] phase 2: monitor — queue scan only")
    from engine.autodream_scheduler import run_scheduler_cycle
    sched = run_scheduler_cycle(
      batch_n=batch_n or 50,
      batch_interval_sec=0,
      output_dir=output_dir,
      quote=quote,
      force_batch=False,
      skip_monitor=False,
      llm_advisory=llm_advisory,
    )
    batch_meta = sched.get("batch")
    monitor = sched.get("monitor")
    result["phases"]["monitor"] = monitor
  else:
    result["phases"]["analyze"] = {"skipped": True}

  # Phase 3: Re-learn with new export rows recorded
  rows = _load_export_rows()
  if rows:
    print(f"[e2e] phase 3: record {len(rows)} export rows into tracker")
    improve2 = run_improvement_cycle(is_crypto=True, record_rows=rows, persist_okf=True)
    result["phases"]["record"] = {"rows": len(rows), "newly_recorded": improve2.get("cycle", {}).get("newly_recorded")}
  else:
    result["phases"]["record"] = {"rows": 0}

  # Phase 4: Execution (paper default)
  if execute or execute_live:
    print("[e2e] phase 4: execute executable rows")
    if execute_live:
      os.environ["EW_EXECUTION_MODE"] = "live"
    from engine.execution_agent import execute_from_csv
    # Paper submit when execute=True; live only with execute_live + EW_EXECUTE_CONFIRM.
    ex = execute_from_csv(dry_run=False)
    result["phases"]["execute"] = {
      "dry_run": ex.get("dry_run"),
      "orders": ex.get("orders_submitted"),
      "blocked": len(ex.get("blocked", [])),
    }

  # Phase 5: Final health + state
  health = run_health_checks()
  save_health(health)
  result["phases"]["health"] = health
  result["finished_at"] = datetime.now(timezone.utc).isoformat()
  result["elapsed_sec"] = (datetime.now(timezone.utc) - t0).total_seconds()
  result["healthy"] = health.get("healthy", False)

  _save_state(result)
  print(f"[e2e] complete healthy={result['healthy']} elapsed={result['elapsed_sec']:.0f}s")
  return result


def e2e_status() -> Dict[str, Any]:
  """Current E2E system status."""
  from engine.improvement_cycle import improvement_report
  from engine.execution_agent import execution_status

  state = {}
  if E2E_STATE.exists():
    try:
      state = json.loads(E2E_STATE.read_text(encoding="utf-8"))
    except json.JSONDecodeError:
      pass

  return {
    "enabled": e2e_enabled(),
    "last_run": state.get("finished_at"),
    "last_healthy": state.get("healthy"),
    "improvement": improvement_report(),
    "execution": execution_status(),
    "health_path": str(Path(os.environ.get("EW_HEALTH_PATH", "output/system/health.json"))),
  }
