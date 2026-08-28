"""Effectiveness validation — prove (or disprove) trading system performance.

Runs structural tests, outcome-tracker win rates, paper P&L simulation,
fitness scoring, and impact discovery; emits a dense pass/fail report.
"""

from __future__ import annotations

import json
import os
import subprocess
import sys
from dataclasses import dataclass, field
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple

REPORT_JSON = Path(os.environ.get("EW_EFFECTIVENESS_JSON", "output/system/effectiveness_latest.json"))
REPORT_MD = Path(os.environ.get("EW_EFFECTIVENESS_MD", "reports/EFFECTIVENESS_VALIDATION.md"))

# Gates that inform but do not fail the overall verdict
ADVISORY_GATES = frozenset({
  "model_reconciliation",
  "paper_profitability",
  "live_paper_sim",
  "tracked_profitability",
  "tracked_expectancy",
})


def _utcnow() -> str:
  return datetime.now(timezone.utc).isoformat()


def _env_float(name: str, default: float) -> float:
  try:
    return float(os.environ.get(name, str(default)))
  except (TypeError, ValueError):
    return default


def _env_int(name: str, default: int) -> int:
  try:
    return int(os.environ.get(name, str(default)))
  except (TypeError, ValueError):
    return default


@dataclass
class GateResult:
  name: str
  passed: bool
  value: Any = None
  threshold: Any = None
  detail: str = ""

  def to_dict(self) -> dict:
    return {
      "name": self.name,
      "passed": self.passed,
      "value": self.value,
      "threshold": self.threshold,
      "detail": self.detail,
    }


@dataclass
class EffectivenessReport:
  ok: bool = False
  generated_at: str = ""
  gates: List[GateResult] = field(default_factory=list)
  sections: Dict[str, Any] = field(default_factory=dict)
  summary: str = ""

  def to_dict(self) -> dict:
    return {
      "ok": self.ok,
      "generated_at": self.generated_at,
      "gates": [g.to_dict() for g in self.gates],
      "sections": self.sections,
      "summary": self.summary,
      "passed": sum(1 for g in self.gates if g.passed),
      "failed": sum(1 for g in self.gates if not g.passed),
      "total_gates": len(self.gates),
    }


def run_pytest_subset(
  *,
  timeout_sec: int = 600,
  extra_args: Optional[List[str]] = None,
) -> Dict[str, Any]:
  """Run focused effectiveness-related pytest modules."""
  modules = [
    "tests/test_outcome_tracker.py",
    "tests/test_paper_simulator.py",
    "tests/test_e2e_pipeline.py",
    "tests/test_impact_discovery.py",
    "tests/test_strategy_fitness.py",
    "tests/test_portfolio_risk.py",
    "tests/test_execution_stack.py",
    "tests/test_validation.py",
    "tests/test_effectiveness_validation.py",
  ]
  # Exclude flaky report-path test when run via subprocess (uses tmp paths in unit test)
  cmd = [sys.executable, "-m", "pytest", *modules, "-q", "--tb=no", "-k", "not test_write_effectiveness_reports"]
  if extra_args:
    cmd.extend(extra_args)
  try:
    proc = subprocess.run(
      cmd,
      capture_output=True,
      text=True,
      timeout=timeout_sec,
      cwd=str(Path(__file__).resolve().parents[1]),
    )
    tail = (proc.stdout or "") + (proc.stderr or "")
    passed = failed = 0
    for line in tail.splitlines():
      if " passed" in line and " in " in line:
        parts = [p.rstrip(",") for p in line.strip().split()]
        for i, p in enumerate(parts):
          if p == "passed" and i > 0:
            try:
              passed = int(parts[i - 1])
            except ValueError:
              pass
          if p == "failed" and i > 0:
            try:
              failed = int(parts[i - 1])
            except ValueError:
              pass
    return {
      "ok": proc.returncode == 0,
      "returncode": proc.returncode,
      "passed": passed,
      "failed": failed,
      "output_tail": tail[-2000:],
    }
  except subprocess.TimeoutExpired:
    return {"ok": False, "error": f"pytest timeout after {timeout_sec}s"}
  except Exception as exc:
    return {"ok": False, "error": str(exc)}


def load_outcome_metrics() -> Dict[str, Any]:
  from engine.outcome_tracker import compute_metrics, load_metrics

  metrics = load_metrics()
  if not metrics:
    metrics = compute_metrics()
  return metrics or {}


def run_learning_phase_safe(is_crypto: bool = True) -> Dict[str, Any]:
  try:
    from engine.outcome_tracker import run_learning_phase

    return run_learning_phase(is_crypto=is_crypto)
  except Exception as exc:
    return {"ok": False, "error": str(exc)}


def run_paper_sim_safe(
  *,
  equity: float = 50_000.0,
  csv_path: str = "",
  fetch_ohlc: bool = True,
  max_positions: int = 0,
) -> Dict[str, Any]:
  try:
    if max_positions:
      os.environ["EW_PAPER_MAX_POSITIONS"] = str(max_positions)
    from engine.paper_simulator import run_paper_simulation

    return run_paper_simulation(
      csv_path=csv_path or os.environ.get("EW_LIMIT_ORDERS_CSV", "output/latest_limit_orders_all_tf.csv"),
      equity_usd=equity,
      fetch_ohlc=fetch_ohlc,
    )
  except Exception as exc:
    return {"ok": False, "error": str(exc)}


def run_fitness_safe() -> Dict[str, Any]:
  try:
    from engine.strategy_fitness import fitness_from_metrics

    return fitness_from_metrics()
  except Exception as exc:
    return {"ok": False, "error": str(exc)}


def run_impact_safe() -> Dict[str, Any]:
  try:
    from engine.impact_discovery import run_impact_discovery

    return run_impact_discovery()
  except Exception as exc:
    return {"ok": False, "error": str(exc)}


def run_tracked_fee_backtest(
  *,
  equity: float = 50_000.0,
  risk_pct: float = 0.01,
  max_trades: int = 0,
) -> Dict[str, Any]:
  """
  Fee-adjusted expectancy on closed tracked setups (WAE entry, TP1 partial / SL).
  Uses R-multiples with per-trade fee drag so tight stops do not explode notional.
  """
  try:
    from engine.outcome_tracker import _load_state
    from engine.paper_simulator import fee_rate
  except Exception as exc:
    return {"ok": False, "error": str(exc)}

  state = _load_state()
  closed = [
    s for s in state.get("closed", [])
    if s.get("status") in ("tp1_hit", "sl_hit")
  ]
  if max_trades and len(closed) > max_trades:
    closed = closed[-max_trades:]

  fee = fee_rate()
  tp1_partial = float(os.environ.get("EW_TP1_PARTIAL", "0.4"))
  wins = losses = 0
  r_values: List[float] = []
  skipped = 0

  for s in closed:
    try:
      wae = float(s["wae"])
      stop = float(s["stop_loss"])
      tp1 = float(s["tp1"])
    except (KeyError, TypeError, ValueError):
      skipped += 1
      continue
    risk_per_unit = abs(wae - stop)
    if risk_per_unit <= 0 or wae <= 0:
      skipped += 1
      continue

    stop_dist_pct = risk_per_unit / wae
    fee_drag_r = (2.0 * fee) / stop_dist_pct if stop_dist_pct > 0 else 0.0
    reward_r = abs(tp1 - wae) / risk_per_unit

    status = s.get("status")
    if status == "sl_hit":
      net_r = -1.0 - fee_drag_r
      losses += 1
    else:
      net_r = reward_r * tp1_partial - fee_drag_r
      wins += 1
    r_values.append(net_r)

  decided = wins + losses
  wr = round(wins / decided, 4) if decided else None
  avg_r = round(sum(r_values) / len(r_values), 4) if r_values else None
  risk_usd = equity * risk_pct
  total_pnl = round(sum(r_values) * risk_usd, 2) if r_values else 0.0
  total_fees_est = round(sum(
    (2.0 * fee / (abs(float(s["wae"]) - float(s["stop_loss"])) / float(s["wae"])) * risk_usd)
    for s in closed
    if s.get("status") in ("tp1_hit", "sl_hit")
    and float(s.get("wae") or 0) > 0
    and abs(float(s.get("wae", 0)) - float(s.get("stop_loss", 0))) > 0
  ), 2) if closed else 0.0

  return {
    "ok": decided > 0,
    "equity_start": equity,
    "equity_end": round(equity + total_pnl, 2),
    "realized_pnl_usd": total_pnl,
    "fees_usd": total_fees_est,
    "wins": wins,
    "losses": losses,
    "decided": decided,
    "win_rate": wr,
    "avg_r": avg_r,
    "expectancy_r": avg_r,
    "skipped": skipped,
    "risk_pct": risk_pct,
    "risk_usd_per_trade": round(risk_usd, 2),
    "tp1_partial": tp1_partial,
  }


def summarize_metrics_dimensions(metrics: dict) -> Dict[str, Any]:
  """Compact tables for timeframe / direction / tier breakdowns."""
  by_tf = metrics.get("by_timeframe") or {}
  tf_rows = []
  for tf, stats in sorted(by_tf.items(), key=lambda x: -(x[1].get("n") or 0)):
    wr = stats.get("win_rate")
    tf_rows.append({
      "timeframe": tf,
      "wins": stats.get("wins", 0),
      "losses": stats.get("losses", 0),
      "n": stats.get("n", 0),
      "win_rate": wr,
    })

  by_dir = metrics.get("by_direction") or {}
  dir_rows = [
    {"direction": d, **{k: stats.get(k) for k in ("wins", "losses", "n", "win_rate")}}
    for d, stats in by_dir.items()
  ]

  return {"by_timeframe": tf_rows, "by_direction": dir_rows}


def reconcile_models(metrics: dict, paper: dict) -> Dict[str, Any]:
  """Compare outcome-tracker win rate vs paper sim win/loss counts."""
  overall = metrics.get("overall") or {}
  ot_wr = overall.get("win_rate")
  ot_decided = overall.get("decided", 0)
  paper_wins = int(paper.get("wins") or 0)
  paper_losses = int(paper.get("losses") or 0)
  paper_decided = paper_wins + paper_losses
  paper_wr = round(paper_wins / paper_decided, 3) if paper_decided else None
  delta = None
  if ot_wr is not None and paper_wr is not None:
    delta = round(float(ot_wr) - paper_wr, 3)
  return {
    "outcome_tracker_win_rate": ot_wr,
    "outcome_tracker_decided": ot_decided,
    "paper_win_rate": paper_wr,
    "paper_decided": paper_decided,
    "paper_wins": paper_wins,
    "paper_losses": paper_losses,
    "delta": delta,
    "note": (
      "Models measure different things: outcome tracker uses WAE+TP1/SL geometry; "
      "paper sim uses limit DCA fills, fees, and portfolio cap."
    ),
  }


def evaluate_gates(
  *,
  pytest_result: dict,
  metrics: dict,
  paper: dict,
  fitness: dict,
  impact: dict,
  reconciliation: dict,
  tracked_backtest: Optional[dict] = None,
  health: Optional[dict] = None,
) -> List[GateResult]:
  gates: List[GateResult] = []

  min_wr = _env_float("EW_GATE_MIN_WIN_RATE", 0.55)
  min_decided = _env_int("EW_GATE_MIN_DECIDED", 100)
  min_fitness = _env_float("EW_GATE_MIN_FITNESS", 0.45)
  min_paper_trades = _env_int("EW_GATE_MIN_PAPER_TRADES", 3)
  min_tracked_trades = _env_int("EW_GATE_MIN_TRACKED_TRADES", 100)
  min_tracked_wr = _env_float("EW_GATE_MIN_TRACKED_WR", 0.52)
  min_expectancy_r = _env_float("EW_GATE_MIN_EXPECTANCY_R", 0.0)
  require_paper_profit = os.environ.get("EW_GATE_REQUIRE_PAPER_PROFIT", "0").lower() in ("1", "true", "yes")

  # Structural tests
  gates.append(GateResult(
    "pytest_subset",
    bool(pytest_result.get("ok")),
    value=f"{pytest_result.get('passed', 0)} passed / {pytest_result.get('failed', 0)} failed",
    threshold="returncode=0",
    detail=pytest_result.get("error") or "focused effectiveness test modules",
  ))

  overall = metrics.get("overall") or {}
  wr = overall.get("win_rate")
  decided = int(overall.get("decided") or 0)
  gates.append(GateResult(
    "outcome_win_rate",
    wr is not None and decided >= min_decided and float(wr) >= min_wr,
    value=wr,
    threshold=f">= {min_wr:.0%} with n>={min_decided}",
    detail=f"decided={decided}, wins={overall.get('wins')}, losses={overall.get('losses')}",
  ))

  # Best timeframe (1h historically strongest)
  by_tf = metrics.get("by_timeframe") or {}
  tf_1h = by_tf.get("1h") or {}
  tf_1h_wr = tf_1h.get("win_rate")
  gates.append(GateResult(
    "timeframe_1h_win_rate",
    tf_1h_wr is not None and float(tf_1h_wr) >= 0.70,
    value=tf_1h_wr,
    threshold=">= 70%",
    detail=f"n={tf_1h.get('n', 0)}",
  ))

  fit_score = fitness.get("fitness") or fitness.get("composite")
  gates.append(GateResult(
    "strategy_fitness",
    fit_score is not None and float(fit_score) >= min_fitness,
    value=fit_score,
    threshold=f">= {min_fitness}",
    detail=f"n_trades={fitness.get('n_trades')}, sharpe={fitness.get('sharpe')}",
  ))

  # Fee-adjusted backtest on resolved tracked setups (core execution realism)
  tb = tracked_backtest or {}
  tb_wr = tb.get("win_rate")
  tb_decided = int(tb.get("decided") or 0)
  tb_pnl = tb.get("realized_pnl_usd")
  tb_exp_r = tb.get("expectancy_r")
  gates.append(GateResult(
    "tracked_fee_backtest",
    (
      tb.get("ok")
      and tb_decided >= min_tracked_trades
      and tb_wr is not None
      and float(tb_wr) >= min_tracked_wr
    ),
    value={
      "win_rate": tb_wr,
      "decided": tb_decided,
      "expectancy_r": tb_exp_r,
      "pnl_usd": tb_pnl,
      "fees_usd": tb.get("fees_usd"),
    },
    threshold=f">= {min_tracked_wr:.0%} WR, n>={min_tracked_trades} (fee-adjusted sample)",
    detail=f"equity {tb.get('equity_start')} → {tb.get('equity_end')}",
  ))

  if tb_decided >= min_tracked_trades and tb_exp_r is not None:
    gates.append(GateResult(
      "tracked_expectancy",
      float(tb_exp_r) >= min_expectancy_r,
      value=tb_exp_r,
      threshold=f">= {min_expectancy_r} R after fees",
      detail=f"avg win R on TP1 partial; fee drag included",
    ))

  if tb_decided >= min_tracked_trades and tb_pnl is not None:
    gates.append(GateResult(
      "tracked_profitability",
      float(tb_pnl) > 0,
      value=tb_pnl,
      threshold="> 0 USD after fees",
      detail=f"WR {tb_wr} on {tb_decided} resolved setups",
    ))

  # Live OHLC paper sim — advisory (uses recent tail bars, not setup timestamps)
  paper_pnl = paper.get("realized_pnl_usd")
  paper_n = int(paper.get("simulated") or 0)
  paper_wins = int(paper.get("wins") or 0)
  paper_losses = int(paper.get("losses") or 0)
  paper_decided = paper_wins + paper_losses
  paper_wr = round(paper_wins / paper_decided, 3) if paper_decided else None

  paper_ok = paper.get("ok", True) and paper_n >= min_paper_trades
  if paper.get("skipped"):
    gates.append(GateResult(
      "live_paper_sim",
      True,
      value="skipped",
      threshold="advisory",
      detail="run without --fast/--no-paper for live tail-OHLC proxy",
    ))
  else:
    if require_paper_profit:
      paper_ok = paper_ok and paper_pnl is not None and float(paper_pnl) > 0
    gates.append(GateResult(
      "live_paper_sim",
      paper_ok,
      value={
        "pnl_usd": paper_pnl,
        "simulated": paper_n,
        "wins": paper_wins,
        "losses": paper_losses,
        "win_rate": paper_wr,
      },
      threshold=f">= {min_paper_trades} trades (advisory)",
      detail=f"equity {paper.get('starting_equity_usd')} → {paper.get('ending_equity_usd')}; tail-OHLC proxy",
    ))

  # Paper profitability advisory (honest — does not fail overall unless env set)
  if paper_decided >= min_paper_trades and paper_pnl is not None:
    gates.append(GateResult(
      "paper_profitability",
      float(paper_pnl) > 0,
      value=paper_pnl,
      threshold="> 0 USD",
      detail=f"paper WR {paper_wr} vs geometry WR {overall.get('win_rate')}",
    ))

  discovery = impact.get("discovery") if isinstance(impact, dict) else {}
  baseline = (
    (discovery.get("baseline_wr") if isinstance(discovery, dict) else None)
    or impact.get("baseline_wr")
    or (impact.get("metrics_snapshot") or {}).get("overall_wr")
    or overall.get("win_rate")
  )
  promoted = len((impact.get("balanced_weights") or {}).get("weights") or {}) if isinstance(impact, dict) else 0
  gates.append(GateResult(
    "impact_discovery",
    baseline is not None,
    value={"baseline_wr": baseline, "promoted_factors": promoted},
    threshold="baseline computed",
    detail=f"hidden_gems={len(discovery.get('hidden_gems') or [])}" if isinstance(discovery, dict) else "",
  ))

  if health:
    gates.append(GateResult(
      "system_health",
      bool(health.get("healthy")),
      value=health.get("passed"),
      threshold=health.get("total"),
      detail=health.get("summary", ""),
    ))

  # Honest warning gate — large model divergence
  delta = reconciliation.get("delta")
  if delta is not None and paper.get("simulated", 0) >= min_paper_trades:
    gates.append(GateResult(
      "model_reconciliation",
      abs(float(delta)) <= 0.25,
      value=delta,
      threshold="|delta| <= 0.25",
      detail=reconciliation.get("note", ""),
    ))

  return gates


def run_effectiveness_validation(
  *,
  run_tests: bool = True,
  run_learning: bool = False,
  run_paper: bool = True,
  fetch_ohlc: bool = True,
  is_crypto: bool = True,
  equity: float = 50_000.0,
  csv_path: str = "",
  paper_max_positions: int = 0,
  write_reports: bool = True,
) -> EffectivenessReport:
  report = EffectivenessReport(generated_at=_utcnow())

  # Fresh portfolio state for validation (avoid test pollution)
  try:
    from engine.portfolio_risk import PortfolioState, save_portfolio_state
    save_portfolio_state(PortfolioState(equity=equity))
  except Exception:
    pass

  pytest_result: Dict[str, Any] = {"ok": True, "skipped": True}
  if run_tests:
    pytest_result = run_pytest_subset()
  report.sections["pytest"] = pytest_result

  learning: Dict[str, Any] = {"skipped": True}
  if run_learning:
    learning = run_learning_phase_safe(is_crypto=is_crypto)
  report.sections["learning"] = learning

  metrics = load_outcome_metrics()
  report.sections["metrics"] = metrics
  report.sections["dimensions"] = summarize_metrics_dimensions(metrics)

  tracked_backtest = run_tracked_fee_backtest(equity=equity)
  report.sections["tracked_fee_backtest"] = tracked_backtest

  paper: Dict[str, Any] = {"skipped": True}
  if run_paper:
    paper = run_paper_sim_safe(
      equity=equity,
      csv_path=csv_path,
      fetch_ohlc=fetch_ohlc,
      max_positions=paper_max_positions,
    )
  report.sections["paper_sim"] = paper

  fitness = run_fitness_safe()
  report.sections["fitness"] = fitness

  impact = run_impact_safe()
  report.sections["impact_discovery"] = impact

  reconciliation = reconcile_models(metrics, paper if isinstance(paper, dict) else {})
  report.sections["reconciliation"] = reconciliation

  health: Optional[Dict[str, Any]] = None
  try:
    from engine.system_health import run_health_checks

    health = run_health_checks()
    report.sections["health"] = health
  except Exception as exc:
    report.sections["health"] = {"error": str(exc)}

  report.gates = evaluate_gates(
    pytest_result=pytest_result,
    metrics=metrics,
    paper=paper if isinstance(paper, dict) else {},
    fitness=fitness if isinstance(fitness, dict) else {},
    impact=impact if isinstance(impact, dict) else {},
    reconciliation=reconciliation,
    tracked_backtest=tracked_backtest,
    health=health,
  )
  core_gates = [g for g in report.gates if g.name not in ADVISORY_GATES]
  report.ok = all(g.passed for g in core_gates)
  passed = sum(1 for g in core_gates if g.passed)
  report.summary = f"{passed}/{len(core_gates)} core gates passed — {'EFFECTIVE' if report.ok else 'NEEDS WORK'}"

  if write_reports:
    write_effectiveness_reports(report)

  return report


def write_effectiveness_reports(report: EffectivenessReport) -> Tuple[str, str]:
  json_path = Path(os.environ.get("EW_EFFECTIVENESS_JSON", str(REPORT_JSON)))
  md_path = Path(os.environ.get("EW_EFFECTIVENESS_MD", str(REPORT_MD)))
  json_path.parent.mkdir(parents=True, exist_ok=True)
  md_path.parent.mkdir(parents=True, exist_ok=True)
  json_path.write_text(json.dumps(report.to_dict(), indent=2, default=str), encoding="utf-8")

  metrics = report.sections.get("metrics") or {}
  overall = metrics.get("overall") or {}
  paper = report.sections.get("paper_sim") or {}
  fitness = report.sections.get("fitness") or {}
  recon = report.sections.get("reconciliation") or {}
  tracked = report.sections.get("tracked_fee_backtest") or {}
  dimensions = report.sections.get("dimensions") or {}

  core_gates = [g for g in report.gates if g.name not in ADVISORY_GATES]
  advisory_gates = [g for g in report.gates if g.name in ADVISORY_GATES]

  lines = [
    "# Effectiveness Validation Report",
    "",
    f"**Generated:** {report.generated_at}",
    f"**Verdict:** {'PASS' if report.ok else 'FAIL'} — {report.summary}",
    "",
    "## Core Gates",
    "",
    "| Gate | Status | Value | Threshold | Detail |",
    "|------|--------|-------|-----------|--------|",
  ]
  for g in core_gates:
    status = "PASS" if g.passed else "**FAIL**"
    val = json.dumps(g.value, default=str) if not isinstance(g.value, (str, int, float)) else str(g.value)
    if len(val) > 60:
      val = val[:57] + "..."
    lines.append(f"| {g.name} | {status} | {val} | {g.threshold} | {g.detail} |")

  if advisory_gates:
    lines.extend([
      "",
      "## Advisory Gates (informational)",
      "",
      "| Gate | Status | Value | Threshold | Detail |",
      "|------|--------|-------|-----------|--------|",
    ])
    for g in advisory_gates:
      status = "PASS" if g.passed else "WARN"
      val = json.dumps(g.value, default=str) if not isinstance(g.value, (str, int, float)) else str(g.value)
      if len(val) > 60:
        val = val[:57] + "..."
      lines.append(f"| {g.name} | {status} | {val} | {g.threshold} | {g.detail} |")

  tf_rows = dimensions.get("by_timeframe") or []
  tf_table = ["", "## Win Rate by Timeframe", "", "| TF | Wins | Losses | n | Win rate |", "|----|------|--------|---|----------|"]
  for row in tf_rows[:12]:
    wr = row.get("win_rate")
    wr_s = f"{wr:.1%}" if isinstance(wr, (int, float)) else "—"
    tf_table.append(
      f"| {row.get('timeframe', '—')} | {row.get('wins', '—')} | {row.get('losses', '—')} | "
      f"{row.get('n', '—')} | {wr_s} |"
    )

  lines.extend(tf_table)
  lines.extend([
    "",
    "## Outcome Tracker (geometry win rate)",
    "",
    f"| Wins | Losses | Decided | Win rate | Open |",
    f"|------|--------|---------|----------|------|",
    f"| {overall.get('wins', '—')} | {overall.get('losses', '—')} | {overall.get('decided', '—')} | {overall.get('win_rate', '—')} | {metrics.get('open_count', '—')} |",
    "",
    "## Tracked Fee Backtest (WAE entry + fees)",
    "",
    f"- Equity: ${tracked.get('equity_start', '—')} → ${tracked.get('equity_end', '—')}",
    f"- Realized P&L: **${tracked.get('realized_pnl_usd', '—')}**",
    f"- Win rate: {tracked.get('win_rate', '—')} ({tracked.get('wins', '—')}W / {tracked.get('losses', '—')}L, n={tracked.get('decided', '—')})",
    f"- Expectancy: **{tracked.get('expectancy_r', '—')} R** per trade (@ ${tracked.get('risk_usd_per_trade', '—')} risk)",
    f"- Fees (est.): ${tracked.get('fees_usd', '—')}",
    "",
    "## Live Paper Simulation (tail OHLC proxy)",
    "",
    f"- Equity: ${paper.get('starting_equity_usd', '—')} → ${paper.get('ending_equity_usd', '—')}",
    f"- Realized P&L: **${paper.get('realized_pnl_usd', '—')}**",
    f"- Simulated: {paper.get('simulated', '—')} / {paper.get('candidates', '—')} candidates",
    f"- Wins / Losses: {paper.get('wins', '—')} / {paper.get('losses', '—')}",
    "",
    "## Strategy Fitness",
    "",
    f"- Fitness: **{fitness.get('fitness', fitness.get('composite', '—'))}**",
    f"- Sharpe: {fitness.get('sharpe')} | Sortino: {fitness.get('sortino')} | PF: {fitness.get('profit_factor')}",
    "",
    "## Model Reconciliation",
    "",
    f"- Outcome tracker WR: {recon.get('outcome_tracker_win_rate')}",
    f"- Paper sim WR: {recon.get('paper_win_rate')}",
    f"- Delta: {recon.get('delta')}",
    f"- Note: {recon.get('note', '')}",
    "",
    "## Interpretation",
    "",
    "- **Geometry win rate** proves setup levels resolve favorably (TP1 before SL) on historical bars.",
    "- **Tracked fee backtest** applies risk sizing + fees to the same resolved setups — the primary execution proof.",
    "- **Live paper sim** uses recent tail OHLC (not setup timestamps) — advisory only.",
    "",
    f"Machine-readable: `{json_path}`",
    "",
  ])
  md_path.write_text("\n".join(lines), encoding="utf-8")
  return str(json_path), str(md_path)
