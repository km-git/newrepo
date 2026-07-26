"""Decoupled AutoResearch — log strategy/risk experiments; never auto-promote to live."""

from __future__ import annotations

import json
import os
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, List, Optional

from engine.strategy_fitness import fitness_from_metrics


EXPERIMENT_LOG = Path(os.environ.get("EW_AUTORESEARCH_LOG", "output/autoresearch/experiments.jsonl"))


def autoresearch_enabled() -> bool:
  return os.environ.get("EW_AUTORESEARCH", "1").lower() not in ("0", "false", "no")


def _append(record: dict) -> None:
  EXPERIMENT_LOG.parent.mkdir(parents=True, exist_ok=True)
  with EXPERIMENT_LOG.open("a", encoding="utf-8") as f:
    f.write(json.dumps(record, default=str) + "\n")


def _read_log(limit: int = 200) -> List[dict]:
  if not EXPERIMENT_LOG.exists():
    return []
  rows: List[dict] = []
  for line in EXPERIMENT_LOG.read_text(encoding="utf-8").splitlines():
    line = line.strip()
    if not line:
      continue
    try:
      rows.append(json.loads(line))
    except json.JSONDecodeError:
      continue
  return rows[-limit:]


def propose_experiments() -> List[Dict[str, Any]]:
  """
  Suggest parameter experiments (human or overnight runner applies them).
  Does not mutate production code — env toggles and documented hypotheses only.
  """
  return [
    {
      "id": "wider_sl_floor",
      "hypothesis": "Raise TF min SL 5% → fewer stop-outs, lower win rate",
      "env": {"EW_TF_STOP_MIN_MULT": "1.05"},
      "risk": "low",
    },
    {
      "id": "stricter_execution_consensus",
      "hypothesis": "Block caution stances → fewer paper orders, higher quality",
      "env": {"EW_EXECUTION_BLOCK_CAUTION": "1"},
      "risk": "medium",
    },
    {
      "id": "dynamic_risk_on",
      "hypothesis": "Scale probe size by hist win rate + TV score",
      "env": {"EW_DYNAMIC_RISK": "1"},
      "risk": "low",
    },
    {
      "id": "llm_execution_panel",
      "hypothesis": "Cursor multi-model gate on every executable row",
      "env": {"EW_EXECUTION_CONSENSUS_LLM": "1", "EW_LLM_BACKEND": "cursor"},
      "risk": "token_cost",
    },
  ]


def record_baseline_fitness(note: str = "baseline") -> Dict[str, Any]:
  """Log current metrics fitness as experiment baseline (no env change)."""
  fit = fitness_from_metrics()
  record = {
    "ts": datetime.now(timezone.utc).isoformat(),
    "experiment_id": note,
    "action": "baseline",
    "env_delta": {},
    "fitness": fit,
    "promoted": False,
  }
  _append(record)
  return record


def run_autoresearch_batch(
  *,
  max_experiments: int = 5,
  record_baseline: bool = True,
) -> Dict[str, Any]:
  """
  Log baseline + proposed experiments with current fitness scores.
  Full re-backtest per variant requires a separate overnight batch runner;
  this keeps research decoupled from live trading (Swarm Trader pattern).
  """
  if not autoresearch_enabled():
    return {"skipped": True, "reason": "EW_AUTORESEARCH disabled"}

  out: Dict[str, Any] = {"proposals": [], "logged": []}
  if record_baseline:
    out["logged"].append(record_baseline_fitness("baseline"))

  baseline_fitness = out["logged"][0]["fitness"]["fitness"] if out["logged"] else fitness_from_metrics()["fitness"]

  for prop in propose_experiments()[:max_experiments]:
    entry = {
      "ts": datetime.now(timezone.utc).isoformat(),
      "experiment_id": prop["id"],
      "action": "proposed",
      "hypothesis": prop["hypothesis"],
      "env_delta": prop["env"],
      "risk": prop["risk"],
      "fitness_at_proposal": baseline_fitness,
      "promoted": False,
      "note": "Run batch with env_delta, re-score fitness, compare to baseline before promote",
    }
    _append(entry)
    out["proposals"].append(entry)

  out["baseline_fitness"] = baseline_fitness
  out["log_path"] = str(EXPERIMENT_LOG)
  return out


def latest_experiments_summary(limit: int = 20) -> Dict[str, Any]:
  rows = _read_log(limit)
  if not rows:
    return {"count": 0, "log_path": str(EXPERIMENT_LOG)}
  best = max(rows, key=lambda r: float((r.get("fitness") or {}).get("fitness") or 0))
  return {
    "count": len(rows),
    "log_path": str(EXPERIMENT_LOG),
    "latest_id": rows[-1].get("experiment_id"),
    "best_fitness": (best.get("fitness") or {}).get("fitness"),
    "best_id": best.get("experiment_id"),
    "pending_promote": [r["experiment_id"] for r in rows if r.get("action") == "proposed" and not r.get("promoted")],
  }
