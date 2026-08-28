"""Autonomous operations — self-learning, PR merge, research, no user input required."""

from __future__ import annotations

import json
import os
import subprocess
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, Optional

TICK_LOG = Path(os.environ.get("EW_AUTONOMOUS_TICK_LOG", "output/autonomous/tick_log.jsonl"))
STATE_PATH = Path(os.environ.get("EW_AUTONOMOUS_STATE", "output/autonomous/ops_state.json"))


def autonomous_enabled() -> bool:
  return os.environ.get("EW_AUTONOMOUS_OPS", "1").lower() not in ("0", "false", "no")


def _utcnow() -> str:
  return datetime.now(timezone.utc).isoformat()


def _append_tick(record: dict) -> None:
  TICK_LOG.parent.mkdir(parents=True, exist_ok=True)
  with TICK_LOG.open("a", encoding="utf-8") as f:
    f.write(json.dumps(record, default=str) + "\n")


def _save_state(state: dict) -> None:
  STATE_PATH.parent.mkdir(parents=True, exist_ok=True)
  STATE_PATH.write_text(json.dumps(state, indent=2, default=str), encoding="utf-8")


def run_pr_auto_merge(*, dry_run: bool = False) -> Dict[str, Any]:
  """Ready draft PRs and auto-approve/merge all open PRs via executive consensus."""
  if os.environ.get("EW_PR_AUTO_MERGE", "1").lower() in ("0", "false", "no"):
    return {"skipped": True, "reason": "EW_PR_AUTO_MERGE off"}

  try:
    from engine.pr_agent import run_pr_agent

    os.environ.setdefault("EW_PR_AUTO_APPROVE", "1")
    os.environ.setdefault("EW_PR_AUTO_MERGE", "1")
    os.environ.setdefault("EW_PR_MERGE_WITHOUT_PANEL", "1")
    os.environ.setdefault("EW_PR_LLM_ADVISORY", "1")
    os.environ.setdefault("EW_LLM_BACKEND", "cursor")
    os.environ.setdefault("EW_PR_AUTO_RESOLVE_CONFLICTS", "1")

    return run_pr_agent(approve_all=True, dry_run=dry_run)
  except Exception as exc:
    return {"ok": False, "error": str(exc)}


def run_self_learning(*, use_llm: bool = True) -> Dict[str, Any]:
  """Improvement cycle + AI multi-model review + OKF lesson persistence."""
  try:
    from engine.improvement_cycle import run_improvement_cycle

    research = {}
    try:
      from engine.deep_research import load_deep_research

      research = load_deep_research()
    except ImportError:
      pass

    # Self-improvement uses LLM; routine sub-tasks stay cheap/off via governor
    return run_improvement_cycle(
      is_crypto=True,
      persist_okf=True,
      use_llm=use_llm,
      paper=research.get("intel"),
    )
  except Exception as exc:
    return {"error": str(exc)}


def run_autoresearch_promote() -> Dict[str, Any]:
  """Evaluate experiments and auto-promote winner when fitness improves."""
  try:
    from engine.autoresearch import auto_promote_best_experiment, run_autoresearch_eval_loop

    eval_result = run_autoresearch_eval_loop()
    promote = auto_promote_best_experiment(eval_result)
    return {"eval": eval_result, "promote": promote}
  except Exception as exc:
    return {"error": str(exc)}


def run_autonomous_tick(
  *,
  skip_pr: bool = False,
  skip_learning: bool = False,
  skip_research: bool = False,
  skip_autoresearch: bool = False,
  pr_dry_run: bool = False,
) -> Dict[str, Any]:
  """
  One autonomous tick — runs without user input:
  1. Self-learning (improvement + OKF + AI models)
  2. Deep research (web scrape, WS, social, impact, AI synthesis)
  3. Autoresearch eval + auto-promote winners
  4. PR auto-approve + merge all open PRs
  5. Health check
  """
  if not autonomous_enabled():
    return {"skipped": True, "reason": "EW_AUTONOMOUS_OPS disabled"}

  tick: Dict[str, Any] = {"timestamp_utc": _utcnow(), "phases": {}}

  if not skip_learning:
    tick["phases"]["learning"] = run_self_learning(use_llm=True)

  if os.environ.get("EW_TOOL_AUDIT", "1").lower() not in ("0", "false", "no"):
    try:
      from engine.tool_resource_audit import run_tool_resource_audit

      tick["phases"]["tool_audit"] = run_tool_resource_audit(persist=True)
    except Exception as exc:
      tick["phases"]["tool_audit"] = {"error": str(exc)}

  if not skip_research:
    try:
      from engine.deep_research import run_deep_research

      tick["phases"]["deep_research"] = run_deep_research(use_ai=True)
    except Exception as exc:
      tick["phases"]["deep_research"] = {"error": str(exc)}

  if not skip_autoresearch:
    tick["phases"]["autoresearch"] = run_autoresearch_promote()

  if os.environ.get("EW_AUTONOMOUS_UNIVERSE_EXECUTE", "0").lower() in ("1", "true", "yes"):
    try:
      from engine.execution_agent import execute_from_csv

      csv_path = os.environ.get("EW_LIMIT_ORDERS_CSV", "output/latest_limit_orders_all_tf.csv")
      tick["phases"]["universe_execute"] = execute_from_csv(
        csv_path,
        dry_run=os.environ.get("EW_EXECUTE_CONFIRM", "0") != "1",
      )
    except Exception as exc:
      tick["phases"]["universe_execute"] = {"error": str(exc)}

  if os.environ.get("EW_AUTONOMOUS_BACKTEST", "0").lower() in ("1", "true", "yes"):
    try:
      from engine.backtest_runner import run_walk_forward_backtest

      tick["phases"]["backtest"] = run_walk_forward_backtest()
    except Exception as exc:
      tick["phases"]["backtest"] = {"error": str(exc)}

  if not skip_pr:
    tick["phases"]["pr_merge"] = run_pr_auto_merge(dry_run=pr_dry_run)

  try:
    from engine.system_health import run_health_checks, save_health

    health = run_health_checks()
    save_health(health)
    tick["health"] = {"healthy": health.get("healthy"), "passed": health.get("passed"), "total": health.get("total")}
  except Exception as exc:
    tick["health"] = {"error": str(exc)}

  tick["ok"] = not any(
    isinstance(v, dict) and v.get("error") and not v.get("skipped")
    for v in tick["phases"].values()
  )

  try:
    from engine.model_budget_governor import governor_summary, other_model_shame_status

    tick["model_budget"] = governor_summary()
    shame = other_model_shame_status()
    tick["model_budget"]["shame"] = shame
    if shame.get("ashamed"):
      print(f"[autonomous] ASHAMED: Other Models at {shame.get('other_share', 0):.1%} — use Cursor Pro")
  except Exception:
    pass

  _append_tick(tick)
  state = {
    "last_tick_utc": tick["timestamp_utc"],
    "last_ok": tick["ok"],
    "last_health": tick.get("health"),
    "tick_count": _tick_count() + 1,
  }
  _save_state(state)
  tick["state"] = state
  return tick


def _tick_count() -> int:
  if not STATE_PATH.exists():
    return 0
  try:
    return int(json.loads(STATE_PATH.read_text()).get("tick_count", 0))
  except (json.JSONDecodeError, OSError, ValueError):
    return 0


def run_full_daily() -> int:
  """Invoke run_autonomous_daily.sh (pytest + full pipeline)."""
  script = Path("scripts/run_autonomous_daily.sh")
  if not script.exists():
    return 1
  proc = subprocess.run(["bash", str(script)], env=os.environ.copy())
  return proc.returncode
