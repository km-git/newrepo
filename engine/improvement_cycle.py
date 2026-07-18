"""Continuous improvement cycle — learning, OKF, health, feedback loop."""

from __future__ import annotations

import json
import os
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, List, Optional

from engine.outcome_tracker import load_metrics, run_learning_phase


CYCLE_LOG = Path(os.environ.get("EW_IMPROVEMENT_LOG", "output/system/improvement_cycles.jsonl"))


def improvement_enabled() -> bool:
  return os.environ.get("EW_IMPROVEMENT_CYCLE", "1").lower() not in ("0", "false", "no")


def run_improvement_cycle(
  *,
  is_crypto: bool = True,
  record_rows: Optional[List[dict]] = None,
  persist_okf: bool = True,
) -> Dict[str, Any]:
  """
  Close the feedback loop:
  1. Resolve tracked setups → metrics
  2. Performance report
  3. OKF lesson extraction from metrics
  4. System health snapshot
  """
  if not improvement_enabled():
    return {"skipped": True, "reason": "EW_IMPROVEMENT_CYCLE disabled"}

  metrics = run_learning_phase(is_crypto=is_crypto, record_rows=record_rows)
  okf = {}
  if persist_okf:
    okf = _persist_metrics_lessons(metrics)

  from engine.system_health import run_health_checks, save_health
  health = run_health_checks()
  save_health(health)

  cycle = {
    "timestamp_utc": datetime.now(timezone.utc).isoformat(),
    "resolved": metrics.get("last_resolved", 0),
    "open_count": metrics.get("open_count", 0),
    "overall_win_rate": (metrics.get("overall") or {}).get("win_rate"),
    "newly_recorded": metrics.get("newly_recorded", 0),
    "okf": okf,
    "health": {"passed": health.get("passed"), "total": health.get("total"), "healthy": health.get("healthy")},
  }

  try:
    from engine.risk_consensus import run_risk_consensus

    risk_consensus = run_risk_consensus(metrics, use_llm=False)
    cycle["risk_consensus"] = risk_consensus
  except Exception as exc:
    cycle["risk_consensus_error"] = str(exc)
    risk_consensus = {"error": str(exc)}

  _append_cycle_log(cycle)
  return {"metrics": metrics, "okf": okf, "health": health, "cycle": cycle, "risk_consensus": cycle.get("risk_consensus")}


def _persist_metrics_lessons(metrics: dict) -> Dict[str, Any]:
  """Write teachable moments from metrics into OKF brain."""
  try:
    from engine.brain_self_improve import persist_lesson, self_improve_enabled
    if not self_improve_enabled():
      return {"persisted": False}
    paths = []
    overall = metrics.get("overall") or {}
    wr = overall.get("win_rate")
    if wr is not None:
      r = persist_lesson(
        "GLOBAL",
        f"tracked win_rate={wr:.0%} decided={overall.get('decided', 0)}",
        source="metrics",
      )
      if r.get("persisted"):
        paths.append(r.get("path"))
    for key, block in list((metrics.get("by_pair_tf") or {}).items())[:5]:
      bwr = block.get("win_rate")
      if bwr is not None and block.get("decided", 0) >= 3:
        if bwr < 0.4:
          lesson = f"{key}: poor win_rate {bwr:.0%} — downgrade sizing"
        elif bwr > 0.55:
          lesson = f"{key}: strong win_rate {bwr:.0%} — boost sizing"
        else:
          continue
        r = persist_lesson(key.split("|")[0] if "|" in key else "PAIR", lesson, source="metrics")
        if r.get("persisted"):
          paths.append(r.get("path"))
    return {"persisted": True, "paths": paths}
  except Exception as exc:
    return {"persisted": False, "error": str(exc)}


def _append_cycle_log(cycle: dict) -> None:
  CYCLE_LOG.parent.mkdir(parents=True, exist_ok=True)
  with CYCLE_LOG.open("a") as f:
    f.write(json.dumps(cycle, default=str) + "\n")


def recent_cycles(limit: int = 10) -> List[dict]:
  if not CYCLE_LOG.exists():
    return []
  rows = []
  for line in CYCLE_LOG.read_text(encoding="utf-8").splitlines():
    if line.strip():
      try:
        rows.append(json.loads(line))
      except json.JSONDecodeError:
        continue
  return rows[-limit:]


def improvement_report() -> Dict[str, Any]:
  metrics = load_metrics()
  return {
    "enabled": improvement_enabled(),
    "metrics_updated": metrics.get("updated"),
    "overall": metrics.get("overall"),
    "open_count": metrics.get("open_count", 0),
    "recent_cycles": recent_cycles(5),
  }
