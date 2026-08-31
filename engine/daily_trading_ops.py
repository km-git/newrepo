"""
Daily trading ops — LLM-free composite tick: proof + GOAT + tactical + health.

Single entry for continuous improvement without AI spend.
"""

from __future__ import annotations

import json
import os
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, Optional

REPORT_PATH = Path(os.environ.get("EW_DAILY_OPS_REPORT", "reports/DAILY_TRADING_OPS.md"))
STATE_PATH = Path(os.environ.get("EW_DAILY_OPS_STATE", "output/autonomous/daily_trading_ops_state.json"))


def _report_path() -> Path:
  return Path(os.environ.get("EW_DAILY_OPS_REPORT", str(REPORT_PATH)))


def _state_path() -> Path:
  return Path(os.environ.get("EW_DAILY_OPS_STATE", str(STATE_PATH)))


def _utcnow() -> str:
  return datetime.now(timezone.utc).isoformat()


def _save_state(state: dict) -> None:
  path = _state_path()
  path.parent.mkdir(parents=True, exist_ok=True)
  path.write_text(json.dumps(state, indent=2, default=str), encoding="utf-8")


def bootstrap_ops_artifacts() -> Dict[str, Any]:
  """Ensure minimal artifacts for health/E2E without full batch run."""
  result: Dict[str, Any] = {"bootstrapped": []}

  metrics_path = Path("output/autodream/metrics.json")
  if not metrics_path.exists():
    try:
      from engine.outcome_tracker import compute_metrics, save_metrics

      save_metrics(compute_metrics())
      result["bootstrapped"].append("metrics")
    except Exception as exc:
      result["metrics_error"] = str(exc)

  sched_path = Path("output/autodream/scheduler_state.json")
  if not sched_path.exists():
    sched_path.parent.mkdir(parents=True, exist_ok=True)
    sched_path.write_text(
      json.dumps({"initialized_at": _utcnow(), "queue": [], "bootstrap": True}, indent=2),
      encoding="utf-8",
    )
    result["bootstrapped"].append("scheduler")

  return result


def _composite_readiness(
  *,
  proof: Optional[dict],
  goat: Optional[dict],
  tactical: Optional[dict],
  health: Optional[dict],
  profit_lab: Optional[dict] = None,
) -> Dict[str, Any]:
  proof_v = (proof or {}).get("verdict", "PROOF_PENDING")
  goat_v = (goat or {}).get("composite_verdict", "UNKNOWN")
  posture = (tactical or {}).get("posture", "NEUTRAL")
  healthy = (health or {}).get("healthy", False)
  profit_v = (profit_lab or {}).get("readiness", {}).get("verdict", "UNKNOWN")
  halted = False
  try:
    from engine.risk_ops import is_halted

    halted = is_halted()
  except Exception:
    pass

  blockers: list[str] = []
  if halted:
    blockers.append("risk_halted")
  if proof_v != "PROOF_GO":
    blockers.append(f"paper_proof_{proof_v}")
  if goat_v == "NO_GO":
    blockers.append("goat_no_go")
  if profit_v == "PROFIT_NO_GO":
    blockers.append("profit_lab_no_go")
  if posture == "DEFENSIVE":
    blockers.append("tactical_defensive")
  if not healthy:
    blockers.append("health_incomplete")

  if not blockers and proof_v == "PROOF_GO" and goat_v == "GO":
    verdict = "DEPLOY_GO"
  elif blockers and ("risk_halted" in blockers or "goat_no_go" in blockers or "profit_lab_no_go" in blockers):
    verdict = "DEPLOY_HOLD"
  else:
    verdict = "DEPLOY_CONDITIONAL"

  return {
    "verdict": verdict,
    "blockers": blockers,
    "proof_verdict": proof_v,
    "goat_verdict": goat_v,
    "profit_lab_verdict": profit_v,
    "tactical_posture": posture,
    "healthy": healthy,
    "halted": halted,
  }


def write_daily_ops_report(tick: dict, path: Optional[Path] = None) -> str:
  path = path or _report_path()
  path.parent.mkdir(parents=True, exist_ok=True)
  readiness = tick.get("readiness") or {}
  lines = [
    "# Daily Trading Ops",
    "",
    f"**Tick:** {tick.get('timestamp_utc', '')}  ",
    f"**Readiness:** `{readiness.get('verdict', 'UNKNOWN')}`  ",
    f"**Resolve mode:** `{tick.get('resolve_mode', 'n/a')}`  ",
    "",
    "## Gates",
    "",
    "| Gate | Value |",
    "|------|-------|",
    f"| Paper proof | {readiness.get('proof_verdict', 'n/a')} |",
    f"| GOAT audit | {readiness.get('goat_verdict', 'n/a')} |",
    f"| Profit lab | {readiness.get('profit_lab_verdict', 'n/a')} |",
    f"| Tactical posture | {readiness.get('tactical_posture', 'n/a')} |",
    f"| Health | {'OK' if readiness.get('healthy') else 'INCOMPLETE'} |",
    f"| Risk halted | {readiness.get('halted')} |",
    "",
  ]
  if readiness.get("blockers"):
    lines.extend(["## Blockers", ""])
    for b in readiness["blockers"]:
      lines.append(f"- {b}")
    lines.append("")
  lines.append(f"> State: `{_state_path()}`")
  text = "\n".join(lines) + "\n"
  path.write_text(text, encoding="utf-8")
  return text


def run_daily_trading_tick(
  *,
  fetch_ohlc: bool = False,
  include_goat_audit: bool = True,
  bootstrap: bool = True,
  resolve_mode: Optional[str] = None,
) -> Dict[str, Any]:
  """
  Next-level daily tick (no LLM):
  1. Bootstrap ops artifacts
  2. Paper forward proof
  3. Tactical posture
  4. GOAT effectiveness audit (walk-forward)
  5. Profit laboratory (fee expectancy + CPCV + cost analytics)
  6. Health + composite readiness
  5. Health + composite readiness


  Resolve modes (EW_RESOLVE_MODE or resolve_mode arg):
  - skip: no OHLC resolve (cron default, ~1s)
  - incremental: resolve stale setups only (EW_RESOLVE_RECHECK_HOURS, default 6h)
  - full: resolve all open setups (weekly / manual)
  """
  tick: Dict[str, Any] = {"timestamp_utc": _utcnow(), "phases": {}}
  if resolve_mode is None:
    from engine.outcome_tracker import _resolve_mode

    resolve_mode = _resolve_mode()
  tick["resolve_mode"] = resolve_mode

  if bootstrap:
    tick["phases"]["bootstrap"] = bootstrap_ops_artifacts()

  try:
    from engine.paper_forward_tracker import run_paper_forward_tick

    tick["phases"]["paper_forward"] = run_paper_forward_tick(
      fetch_ohlc=fetch_ohlc,
      include_effectiveness=False,
      resolve_mode=resolve_mode,
    )
  except Exception as exc:
    tick["phases"]["paper_forward"] = {"error": str(exc)}

  try:
    from engine.tactical_safeguard import assess_tactical_posture

    tick["phases"]["tactical"] = assess_tactical_posture()
  except Exception as exc:
    tick["phases"]["tactical"] = {"error": str(exc)}

  goat = None
  if include_goat_audit:
    try:
      from engine.effectiveness_audit import run_full_effectiveness_audit

      goat = run_full_effectiveness_audit(
        fetch_ohlc=fetch_ohlc and os.environ.get("EW_EFFECTIVENESS_PAPER", "0") == "1",
        include_walk_forward=True,
      )
      tick["phases"]["goat_audit"] = goat
    except Exception as exc:
      tick["phases"]["goat_audit"] = {"error": str(exc)}

  profit_lab = None
  if os.environ.get("EW_PROFIT_LAB", "1").lower() not in ("0", "false", "no"):
    try:
      from engine.profit_lab.runner import run_profit_lab

      profit_lab = run_profit_lab(
        run_sweep=os.environ.get("EW_PROFIT_LAB_SWEEP", "0") == "1",
        write_reports=True,
        apply_expectancy_gates=True,
      )
      tick["phases"]["profit_lab"] = {
        "readiness": profit_lab.get("readiness"),
        "overall_expectancy_r": (profit_lab.get("expectancy") or {}).get("overall", {}).get("expectancy_r"),
        "cpcv_verdict": (profit_lab.get("cpcv") or {}).get("deployment_gate", {}).get("verdict"),
      }
    except Exception as exc:
      tick["phases"]["profit_lab"] = {"error": str(exc)}

  health = None
  try:
    from engine.system_health import run_health_checks, save_health

    health = run_health_checks()
    save_health(health)
    tick["phases"]["health"] = {
      "healthy": health.get("healthy"),
      "passed": health.get("passed"),
      "total": health.get("total"),
    }
  except Exception as exc:
    tick["phases"]["health"] = {"error": str(exc)}

  proof = (tick["phases"].get("paper_forward") or {}).get("proof")
  tactical = tick["phases"].get("tactical") if isinstance(tick["phases"].get("tactical"), dict) else None
  tick["readiness"] = _composite_readiness(
    proof=proof,
    goat=goat,
    tactical=tactical,
    health=health,
    profit_lab=profit_lab,
  )
  write_daily_ops_report(tick)

  tick["ok"] = tick["readiness"]["verdict"] != "DEPLOY_HOLD"
  state = {
    "last_tick_utc": tick["timestamp_utc"],
    "readiness_verdict": tick["readiness"]["verdict"],
    "proof_verdict": tick["readiness"].get("proof_verdict"),
    "goat_verdict": tick["readiness"].get("goat_verdict"),
    "profit_lab_verdict": tick["readiness"].get("profit_lab_verdict"),
    "tactical_posture": tick["readiness"].get("tactical_posture"),
  }
  _save_state(state)
  tick["state"] = state
  return tick
