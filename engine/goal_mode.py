"""Goal-mode orchestration — autonomous research → validate → paper deploy with human gate."""

from __future__ import annotations

import json
import os
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, Optional

DEFAULT_GOAL = (
  "Improve risk-adjusted returns on EW + harmonic limit setups "
  "(probe sizing, dynamic SL/TP, multi-model consensus before paper submit)."
)

GOAL_MODE_REPORT = Path(os.environ.get("EW_GOAL_MODE_REPORT", "output/goal_mode/last_run.json"))


def save_goal_mode_report(result: Dict[str, Any]) -> str:
  GOAL_MODE_REPORT.parent.mkdir(parents=True, exist_ok=True)
  GOAL_MODE_REPORT.write_text(json.dumps(result, indent=2, default=str), encoding="utf-8")
  return str(GOAL_MODE_REPORT)


def goal_mode_enabled() -> bool:
  return os.environ.get("EW_GOAL_MODE", "0").lower() in ("1", "true", "yes")


def auto_deploy_allowed() -> bool:
  """Live capital never auto-deploys; paper needs explicit flag."""
  if os.environ.get("EW_EXECUTE_LIVE", "").lower() in ("1", "true", "yes"):
    return os.environ.get("EW_GOAL_MODE_AUTO_LIVE", "0").lower() in ("1", "true", "yes")
  return os.environ.get("EW_GOAL_MODE_AUTO_PAPER", "1").lower() not in ("0", "false", "no")


def swarm_agent_map() -> Dict[str, str]:
  """How this repo maps to multi-agent swarm roles (Swarm Trader / NexusTrade analogy)."""
  return {
    "ew_engines": "Quant + structure (pyharmonics, EWA, wave consensus)",
    "executive": "Portfolio manager — staged GO / probe tiers",
    "llm_panel": "Analyst swarm — cheap screen + premium tiebreaker (Cursor Pro)",
    "brain_okf": "Memory + cross-run lessons (OKF secondary brain)",
    "risk_manager": "Code-enforced: dynamic SL, tier caps, execution_consensus, drawdown halt",
    "impact_discovery": "Research — hidden factor lifts from outcomes",
    "social_validation": "Web/forum strategy critique",
    "tv_oss_consensus": "Indicator stack curation (no sprawl)",
    "autodream": "Fast geometry backtest on recent bars",
    "outcome_tracker": "Walk-forward resolution on tracked setups",
    "autoresearch": "Decoupled experiment log — human promotes to production",
    "paper_ledger": "Alpaca/ccxt analogue — paper default",
  }


def run_goal_mode_cycle(
  goal: Optional[str] = None,
  *,
  batch_n: int = 50,
  llm_advisory: bool = False,
  execute_paper: Optional[bool] = None,
  **e2e_kwargs: Any,
) -> Dict[str, Any]:
  """
  Goal-mode loop:
  1. Research — impact, social, TV OSS, brain memory
  2. Backtest — tracked outcomes + composite fitness
  3. Validate — risk consensus + execution consensus rules
  4. Deploy — paper execute (human gate for live)
  """
  from engine.e2e_pipeline import run_e2e_cycle
  from engine.strategy_fitness import fitness_from_metrics
  from engine.outcome_tracker import load_metrics

  goal_text = goal or os.environ.get("EW_GOAL_MODE_TEXT", DEFAULT_GOAL)
  os.environ.setdefault("EW_HEALTH_REQUIRE_ARTIFACTS", "0")
  paper = execute_paper if execute_paper is not None else auto_deploy_allowed()

  live_req = bool(e2e_kwargs.pop("execute_live", False))
  e2e_kwargs.pop("execute", None)
  allow_live = (
    live_req
    and os.environ.get("EW_EXECUTE_CONFIRM", "") == "1"
    and os.environ.get("EW_GOAL_MODE_AUTO_LIVE", "0").lower() in ("1", "true", "yes")
  )
  do_execute = paper or allow_live

  e2e = run_e2e_cycle(
    batch_n=batch_n,
    llm_advisory=llm_advisory,
    execute=do_execute,
    execute_live=allow_live,
    **e2e_kwargs,
  )

  metrics = load_metrics()
  fitness = fitness_from_metrics(metrics)

  research = {}
  imp = (e2e.get("phases") or {}).get("learn") or {}
  rec = (e2e.get("phases") or {}).get("record") or {}
  research["learning"] = imp
  research["recorded_rows"] = rec

  validate: Dict[str, Any] = {"fitness": fitness, "human_gate": {}}
  validate["human_gate"]["paper_auto"] = paper
  validate["human_gate"]["live_allowed"] = allow_live
  validate["human_gate"]["live_requires"] = (
    "EW_GOAL_MODE_AUTO_LIVE=1 + EW_EXECUTE_CONFIRM=1 + --execute-live"
  )
  try:
    from engine.risk_consensus import run_risk_consensus

    validate["risk_consensus"] = run_risk_consensus(metrics, use_llm=llm_advisory)
  except Exception as exc:
    validate["risk_consensus_error"] = str(exc)

  try:
    from engine.autoresearch import latest_experiments_summary

    validate["autoresearch"] = latest_experiments_summary()
  except Exception:
    pass

  deploy = (e2e.get("phases") or {}).get("execute") or {"skipped": not paper}

  autoresearch_out: Optional[Dict[str, Any]] = None
  if os.environ.get("EW_GOAL_MODE_AUTORESEARCH", "1").lower() not in ("0", "false", "no"):
    try:
      from engine.autoresearch import run_autoresearch_batch

      max_exp = int(os.environ.get("EW_AUTORESEARCH_MAX", "5"))
      autoresearch_out = run_autoresearch_batch(max_experiments=max_exp)
      research["autoresearch"] = autoresearch_out
    except Exception as exc:
      research["autoresearch_error"] = str(exc)

  result = {
    "ok": e2e.get("ok"),
    "healthy": e2e.get("healthy"),
    "goal": goal_text,
    "agents": swarm_agent_map(),
    "phases": {
      "research": research,
      "backtest": fitness,
      "validate": validate,
      "deploy": deploy,
    },
    "e2e": e2e,
    "paradigm": "research → backtest → validate → paper deploy (live gated)",
    "report_path": save_goal_mode_report({
      "ok": e2e.get("ok"),
      "healthy": e2e.get("healthy"),
      "goal": goal_text,
      "backtest_fitness": fitness.get("fitness"),
      "deploy": deploy,
      "finished_at": datetime.now(timezone.utc).isoformat(),
    }),
  }
  return result
