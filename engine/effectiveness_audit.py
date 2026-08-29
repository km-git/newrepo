"""GOAT effectiveness audit — walk-forward, gates, regime analysis, deployment verdict."""

from __future__ import annotations

import json
import os
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, List, Optional

from engine.effectiveness_gates import evaluate_gate, evaluate_regime_gates, gate_thresholds
from engine.strategy_fitness import composite_fitness, fitness_from_metrics, profit_factor, sharpe_ratio
from engine.walk_forward_validator import run_walk_forward_validation

REPORT_PATH = Path("reports/EFFECTIVENESS_AUDIT.md")
JSON_PATH = Path("output/effectiveness/audit.json")


def _report_path() -> Path:
  return Path(os.environ.get("EW_EFFECTIVENESS_REPORT", str(REPORT_PATH)))


def _json_path() -> Path:
  return Path(os.environ.get("EW_EFFECTIVENESS_JSON", str(JSON_PATH)))


def _utcnow() -> str:
  return datetime.now(timezone.utc).isoformat()


def run_paper_gate_audit(*, fetch_ohlc: bool = False) -> Dict[str, Any]:
  """Paper simulation gate — dollar P&L path."""
  from engine.backtest_runner import run_walk_forward_backtest

  bt = run_walk_forward_backtest(fetch_ohlc=fetch_ohlc)
  if not bt.get("ok"):
    return {"ok": False, "reason": bt.get("reason", "backtest_failed"), "backtest": bt}

  paper = bt.get("paper") or {}
  rets: List[float] = []
  for t in paper.get("trades") or []:
    pnl = t.get("realized_pnl_usd")
    risk = t.get("risk_budget_usd") or paper.get("starting_equity_usd", 10000) * 0.01
    if pnl is not None and risk and float(risk) > 0:
      rets.append(float(pnl) / float(risk))

  gate = evaluate_gate(
    n_trades=bt.get("wins", 0) + bt.get("losses", 0),
    win_rate=bt.get("win_rate"),
    sharpe=paper.get("sharpe") or bt.get("sharpe"),
    profit_factor=paper.get("profit_factor") or bt.get("profit_factor"),
    return_pct=paper.get("return_pct") or bt.get("return_pct"),
    max_dd_pct=paper.get("max_drawdown_pct"),
    returns=rets or None,
    wins=bt.get("wins"),
  )
  return {"ok": True, "backtest": bt, "gate": gate, "source": "paper_simulation"}


def run_outcome_gate_audit() -> Dict[str, Any]:
  """Tracked outcome gate — forward resolution path."""
  from engine.outcome_tracker import _dedupe_closed, _load_state, compute_metrics, save_metrics
  from engine.execution_gates import filter_closed_for_policy
  from engine.strategy_fitness import r_returns_from_closed
  from engine.walk_forward_validator import _metrics_from_returns

  metrics = compute_metrics()
  save_metrics(metrics)
  regime = evaluate_regime_gates(metrics)

  state = _load_state()
  closed = _dedupe_closed([
    s for s in state.get("closed", []) if s.get("status") in ("tp1_hit", "sl_hit")
  ])
  policy_closed = filter_closed_for_policy(closed, metrics)
  rets = r_returns_from_closed(policy_closed)
  policy_metrics = _metrics_from_returns(rets)

  fit = fitness_from_metrics(metrics)
  overall = metrics.get("overall") or {}

  gate = evaluate_gate(
    n_trades=policy_metrics.get("n", 0),
    win_rate=policy_metrics.get("win_rate"),
    sharpe=policy_metrics.get("sharpe"),
    profit_factor=policy_metrics.get("profit_factor"),
    return_pct=policy_metrics.get("return_pct"),
    max_dd_pct=policy_metrics.get("max_drawdown_pct"),
    returns=policy_metrics.get("returns"),
    wins=policy_metrics.get("wins"),
    num_trials=int(os.environ.get("EW_AUTORESEARCH_TRIALS", "5")),
  )
  return {
    "ok": True,
    "metrics": metrics,
    "policy_filtered_n": len(policy_closed),
    "policy_metrics": {k: v for k, v in policy_metrics.items() if k != "returns"},
    "fitness": fit,
    "regime": regime,
    "gate": gate,
    "source": "tracked_outcomes",
  }


def run_full_effectiveness_audit(
  *,
  fetch_ohlc: bool = False,
  include_walk_forward: bool = True,
) -> Dict[str, Any]:
  """
  Full GOAT audit:
  1. Walk-forward OOS on tracked setups
  2. Outcome gate (historical forward resolution)
  3. Regime gates (per-TF)
  4. Paper simulation gate (optional OHLC fetch)
  5. Composite deployment verdict
  """
  result: Dict[str, Any] = {
    "audited_at": _utcnow(),
    "thresholds": gate_thresholds(),
  }

  if include_walk_forward:
    result["walk_forward"] = run_walk_forward_validation(
      num_trials=int(os.environ.get("EW_AUTORESEARCH_TRIALS", "5")),
    )

  result["outcomes"] = run_outcome_gate_audit()

  if fetch_ohlc or os.environ.get("EW_EFFECTIVENESS_PAPER", "0") == "1":
    result["paper"] = run_paper_gate_audit(fetch_ohlc=fetch_ohlc)
  else:
    result["paper"] = {"ok": False, "skipped": True, "reason": "set EW_EFFECTIVENESS_PAPER=1 to run"}

  # Composite verdict — strictest wins
  verdicts = []
  wf = result.get("walk_forward") or {}
  if wf.get("deployment_gate"):
    verdicts.append(wf["deployment_gate"].get("verdict"))
  outcomes_gate = (result.get("outcomes") or {}).get("gate") or {}
  verdicts.append(outcomes_gate.get("verdict"))
  regime_ok = (result.get("outcomes") or {}).get("regime", {}).get("regime_gate_passed", True)
  paper = result.get("paper") or {}
  if paper.get("skipped"):
    pass
  elif not paper.get("ok"):
    verdicts.append("NO_GO")
  else:
    paper_gate = paper.get("gate") or {}
    if paper_gate:
      verdicts.append(paper_gate.get("verdict"))

  if "NO_GO" in verdicts:
    composite = "NO_GO"
  elif all(v in ("GO", None) for v in verdicts if v) and regime_ok:
    composite = "GO"
  elif "INSUFFICIENT_DATA" in verdicts:
    composite = "INSUFFICIENT_DATA"
  else:
    composite = "CONDITIONAL"

  result["composite_verdict"] = composite
  result["regime_gate_passed"] = regime_ok
  result["recommendations"] = _build_recommendations(result)

  jp = _json_path()
  jp.parent.mkdir(parents=True, exist_ok=True)
  jp.write_text(json.dumps(result, indent=2, default=str), encoding="utf-8")
  write_effectiveness_report(result)
  return result


def _build_recommendations(audit: dict) -> List[str]:
  recs: List[str] = []
  regime = (audit.get("outcomes") or {}).get("regime") or {}
  weak = regime.get("weak_timeframes") or []
  strong = regime.get("strong_timeframes") or []

  if weak:
    recs.append(f"Downgrade or block weak timeframes: {', '.join(weak)} (WR < 40%)")
  if strong:
    recs.append(f"Prioritize strong timeframes: {', '.join(strong)} (WR ≥ 55%)")

  wf = audit.get("walk_forward") or {}
  gate = wf.get("deployment_gate") or {}
  for g in gate.get("gates") or []:
    if not g.get("passed"):
      recs.append(f"Fix gate failure: {g.get('gate')} — {g.get('detail')}")

  psr = (gate.get("psr") or {}).get("psr")
  mtrl = (gate.get("psr") or {}).get("mtrl")
  if psr is not None and psr < 0.95 and mtrl:
    recs.append(f"Need ~{mtrl} more trades for 95% PSR significance at current Sharpe")

  if audit.get("composite_verdict") == "NO_GO":
    recs.append("Do NOT promote to live — address gate failures first")
  elif audit.get("composite_verdict") == "INSUFFICIENT_DATA":
    recs.append("Continue paper trading — insufficient statistical evidence")
  elif audit.get("composite_verdict") == "GO":
    recs.append("Eligible for staged live deployment (25% capital, kill switches active)")

  if not recs:
    recs.append("Continue monitoring — no critical issues detected")
  return recs


def write_effectiveness_report(audit: dict, path: Optional[Path] = None) -> str:
  path = path or _report_path()
  path.parent.mkdir(parents=True, exist_ok=True)

  lines = [
    "# Effectiveness Audit (GOAT Validation)",
    "",
    f"**Audited:** {audit.get('audited_at', '')}  ",
    f"**Composite verdict:** `{audit.get('composite_verdict', 'UNKNOWN')}`  ",
  ]

  wf = audit.get("walk_forward") or {}
  if wf.get("ok"):
    gate = wf.get("deployment_gate") or {}
    stitched = wf.get("stitched_oos") or {}
    lines.extend([
      "",
      "## Walk-forward OOS",
      "",
      f"| Folds | Closed setups | OOS trades | OOS Sharpe | Verdict |",
      f"|-------|---------------|------------|------------|---------|",
      f"| {wf.get('n_folds', 0)} | {wf.get('n_closed', 0)} | {stitched.get('n', 0)} | "
      f"{stitched.get('sharpe', 'n/a')} | {gate.get('verdict', 'n/a')} |",
    ])
    lines.append("")
    lines.append("### Gate results")
    lines.append("")
    lines.append("| Gate | Passed | Detail |")
    lines.append("|------|--------|--------|")
    for g in gate.get("gates") or []:
      mark = "✓" if g.get("passed") else "✗"
      lines.append(f"| {g.get('gate')} | {mark} | {g.get('detail')} |")

  outcomes = audit.get("outcomes") or {}
  regime = outcomes.get("regime") or {}
  if regime.get("regimes"):
    lines.extend(["", "## Regime analysis (by timeframe)", ""])
    lines.append("| TF | Status | n | Win rate |")
    lines.append("|----|--------|---|----------|")
    for r in regime["regimes"]:
      wr = r.get("win_rate")
      wr_s = f"{wr:.1%}" if wr is not None else "n/a"
      lines.append(f"| {r.get('timeframe')} | {r.get('status')} | {r.get('n')} | {wr_s} |")

  lines.extend(["", "## Recommendations", ""])
  for rec in audit.get("recommendations") or []:
    lines.append(f"- {rec}")

  lines.extend([
    "",
    "> Institutional gates: PSR ≥ 0.95, min 250 trades, Sharpe ≥ 0.5, PF ≥ 1.1, max DD ≤ 15%",
    f"> JSON: `{_json_path()}`",
  ])

  text = "\n".join(lines)
  path.write_text(text, encoding="utf-8")
  return text
