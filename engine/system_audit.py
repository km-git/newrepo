"""Brutally honest system health audit — no vanity metrics."""

from __future__ import annotations

import json
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, List, Optional

AUDIT_PATH = Path("output/autodream/system_audit.json")

# Minimum bar for calling the system "working"
MIN_EXECUTABLE_WIN_RATE = 0.52
MIN_OOS_WIN_RATE = 0.50
MIN_READINESS_PREDICTIVE_WR = 0.50
MAX_HEDGE_RATIO = 0.35
MAX_CAUTION_RATIO = 0.50


def audit_paper_trades(trades: List[dict]) -> dict:
  closed = [t for t in trades if t.get("paper_outcome") in ("win", "loss")]
  exec_closed = [
    t for t in closed
    if t.get("status") == "executable" and t.get("execution_tier") in ("full", "probe")
  ]
  all_wr = None
  exec_wr = None
  if closed:
    all_wr = round(sum(1 for t in closed if t["paper_outcome"] == "win") / len(closed), 3)
  if exec_closed:
    exec_wr = round(sum(1 for t in exec_closed if t["paper_outcome"] == "win") / len(exec_closed), 3)
  return {
    "all_setups_closed": len(closed),
    "all_win_rate": all_wr,
    "executable_closed": len(exec_closed),
    "executable_win_rate": exec_wr,
  }


def audit_setups(setup_rows: List[dict]) -> dict:
  if not setup_rows:
    return {"available": False}
  n = len(setup_rows)
  executable = sum(1 for r in setup_rows if r.get("status") == "executable")
  full = sum(1 for r in setup_rows if r.get("execution_tier") == "full")
  hedged = sum(1 for r in setup_rows if r.get("hedge_plan"))
  caution = sum(1 for r in setup_rows if r.get("autodream_verdict") == "caution")
  validated = sum(1 for r in setup_rows if r.get("autodream_verdict") == "validated")

  # Does readiness predict wins?
  hi_w = hi_l = lo_w = lo_l = 0
  for r in setup_rows:
    po = r.get("paper_outcome")
    if po not in ("win", "loss"):
      continue
    rd = float(r.get("readiness_score") or 0)
    if rd >= 65:
      if po == "win":
        hi_w += 1
      else:
        hi_l += 1
    else:
      if po == "win":
        lo_w += 1
      else:
        lo_l += 1
  hi_wr = round(hi_w / (hi_w + hi_l), 3) if hi_w + hi_l else None

  oos = [float(r["oos_win_rate"]) for r in setup_rows if r.get("oos_win_rate")]
  is_rates = [float(r["hist_win_rate"]) for r in setup_rows if r.get("hist_win_rate")]
  perfect_is = sum(1 for x in is_rates if x >= 0.99)

  return {
    "available": True,
    "total_setups": n,
    "executable": executable,
    "full_executable": full,
    "hedge_ratio": round(hedged / n, 3),
    "caution_ratio": round(caution / n, 3),
    "validated_ratio": round(validated / n, 3),
    "readiness_ge65_win_rate": hi_wr,
    "oos_avg": round(sum(oos) / len(oos), 3) if oos else None,
    "is_avg": round(sum(is_rates) / len(is_rates), 3) if is_rates else None,
    "suspicious_perfect_is": perfect_is,
  }


def compute_verdict(paper: dict, setups: dict) -> dict:
  failures: List[str] = []
  warnings: List[str] = []

  exec_wr = paper.get("executable_win_rate")
  if exec_wr is not None and exec_wr < MIN_EXECUTABLE_WIN_RATE:
    failures.append(f"executable paper win rate {exec_wr:.0%} < {MIN_EXECUTABLE_WIN_RATE:.0%}")
  elif exec_wr is None:
    warnings.append("no closed executable paper trades to score")

  oos = setups.get("oos_avg")
  if oos is not None and oos < MIN_OOS_WIN_RATE:
    failures.append(f"OOS avg {oos:.0%} < {MIN_OOS_WIN_RATE:.0%}")

  hi_wr = setups.get("readiness_ge65_win_rate")
  if hi_wr is not None and hi_wr < MIN_READINESS_PREDICTIVE_WR:
    failures.append(f"readiness≥65 win rate {hi_wr:.0%} — indicators not predictive")

  if setups.get("hedge_ratio", 0) > MAX_HEDGE_RATIO:
    warnings.append(f"hedge on {setups.get('hedge_ratio', 0):.0%} setups — SL geometry was broken")

  if setups.get("caution_ratio", 0) > MAX_CAUTION_RATIO:
    warnings.append(f"{setups.get('caution_ratio', 0):.0%} setups in CAUTION")

  if setups.get("suspicious_perfect_is", 0) > 10:
    warnings.append(f"{setups['suspicious_perfect_is']} setups with ≥99% IS — backtest inflated")

  if setups.get("full_executable", 0) == 0:
    warnings.append("zero FULL executables — EW+zone gate never passes")

  if failures:
    status = "FAIL"
    shame = "System is NOT achieving tradeable edge. Do not trust executable labels."
  elif warnings:
    status = "WARN"
    shame = "Marginal system. Paper before live. Probe size only."
  else:
    status = "PASS"
    shame = "Metrics meet minimum bars — still verify out-of-sample."

  return {
    "status": status,
    "shame_note": shame,
    "failures": failures,
    "warnings": warnings,
  }


def run_system_audit(
  paper_trades: List[dict],
  setup_rows: Optional[List[dict]] = None,
) -> dict:
  """Full honest audit after batch."""
  paper = audit_paper_trades(paper_trades)
  setups = audit_setups(setup_rows or [])
  verdict = compute_verdict(paper, setups)
  doc = {
    "updated": datetime.now(timezone.utc).isoformat(),
    "paper": paper,
    "setups": setups,
    "verdict": verdict,
  }
  AUDIT_PATH.parent.mkdir(parents=True, exist_ok=True)
  AUDIT_PATH.write_text(json.dumps(doc, indent=2))
  return doc


def apply_audit_demotions(outcomes: dict, audit: dict) -> dict:
  """Demote executable→monitor when system audit FAILs on edge."""
  v = audit.get("verdict", {})
  if v.get("status") != "FAIL":
    return outcomes
  for style, setup in outcomes.get("setups", {}).items():
    if setup.get("status") != "executable":
      continue
    paper_wr = audit.get("paper", {}).get("executable_win_rate")
    if paper_wr is not None and paper_wr < MIN_EXECUTABLE_WIN_RATE:
      setup["status"] = "monitor"
      setup["execution_tier"] = "none"
      setup["honest_reason"] = (
        setup.get("honest_reason", "")
        + f" · AUDIT FAIL: system executable WR {paper_wr:.0%} — demoted to monitor"
      )
  outcomes.setdefault("autodream", {})["system_audit"] = v
  return outcomes
