"""Orchestrate profit laboratory — north star: fee-adjusted expectancy."""

from __future__ import annotations

import json
import os
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, Optional

REPORT_MD = Path(os.environ.get("EW_PROFIT_LAB_REPORT", "reports/PROFIT_LAB.md"))
STATE_JSON = Path(os.environ.get("EW_PROFIT_LAB_STATE", "output/profit_lab/latest.json"))


def _report_path() -> Path:
  return Path(os.environ.get("EW_PROFIT_LAB_REPORT", str(REPORT_MD)))


def _state_json_path() -> Path:
  return Path(os.environ.get("EW_PROFIT_LAB_STATE", str(STATE_JSON)))


def _utcnow() -> str:
  return datetime.now(timezone.utc).isoformat()


def composite_verdict(
  *,
  expectancy: dict,
  cpcv: dict,
  cost: dict,
  sweep: Optional[dict] = None,
) -> Dict[str, Any]:
  """PROFIT_GO | PROFIT_CONDITIONAL | PROFIT_NO_GO — fee expectancy is boss."""
  blockers: list[str] = []
  overall = (expectancy or {}).get("overall") or {}
  if not overall.get("passes_gate"):
    blockers.append("overall_expectancy_fail")
  cpcv_gate = (cpcv or {}).get("deployment_gate") or {}
  if cpcv_gate.get("verdict") == "NO_GO":
    blockers.append("cpcv_no_go")
  if cost.get("equity_end", 0) < cost.get("equity_start", 50_000):
    blockers.append("negative_equity_curve")
  best_exp = (sweep or {}).get("best", {}).get("expectancy_r")
  if best_exp is not None and best_exp < 0:
    blockers.append("sweep_best_still_negative")

  if not blockers and overall.get("passes_gate") and cpcv_gate.get("passed"):
    verdict = "PROFIT_GO"
  elif blockers and ("overall_expectancy_fail" in blockers or "negative_equity_curve" in blockers):
    verdict = "PROFIT_NO_GO"
  else:
    verdict = "PROFIT_CONDITIONAL"

  return {
    "verdict": verdict,
    "blockers": blockers,
    "north_star_expectancy_r": overall.get("expectancy_r"),
    "cpcv_verdict": cpcv_gate.get("verdict"),
  }


def write_profit_lab_report(result: dict, path: Optional[Path] = None) -> str:
  path = path or _report_path()
  path.parent.mkdir(parents=True, exist_ok=True)
  readiness = result.get("readiness") or {}
  exp = result.get("expectancy") or {}
  overall = exp.get("overall") or {}
  cpcv = result.get("cpcv") or {}
  stitched = cpcv.get("stitched_oos") or {}
  cost = result.get("cost_analytics") or {}
  sweep = result.get("vectorbt_sweep") or {}
  best = sweep.get("best") or {}

  lines = [
    "# Profit Laboratory",
    "",
    f"**Run:** {result.get('timestamp_utc', '')}  ",
    f"**Verdict:** `{readiness.get('verdict', 'UNKNOWN')}`  ",
    "",
    "## North star (fee-adjusted expectancy)",
    "",
    f"| Metric | Value |",
    f"|--------|-------|",
    f"| Overall expectancy (R) | {overall.get('expectancy_r', 'n/a')} |",
    f"| Overall n | {overall.get('n', 'n/a')} |",
    f"| CPCV OOS expectancy (R) | {stitched.get('expectancy_r', 'n/a')} |",
    f"| CPCV verdict | {(cpcv.get('deployment_gate') or {}).get('verdict', 'n/a')} |",
    f"| Equity (fee-adj backtest) | ${cost.get('equity_start', 'n/a')} → ${cost.get('equity_end', 'n/a')} |",
    f"| Breakeven extra bps | {cost.get('breakeven_extra_bps', 'n/a')} |",
    "",
  ]

  if readiness.get("blockers"):
    lines.extend(["## Blockers", ""])
    for b in readiness["blockers"]:
      lines.append(f"- {b}")
    lines.append("")

  if best:
    lines.extend([
      "## vectorbt sweep — best filter combo",
      "",
      f"- Blocked TFs: `{best.get('blocked_tfs')}`",
      f"- Blocked directions: `{best.get('blocked_directions')}`",
      f"- Min stop %: {best.get('min_stop_pct')}",
      f"- Expectancy R: **{best.get('expectancy_r')}** (n={best.get('n')})",
      "",
    ])
    rec = sweep.get("recommended_env") or {}
    if rec:
      lines.append("Recommended env:")
      lines.append("```")
      for k, v in rec.items():
        if v:
          lines.append(f"{k}={v}")
      lines.append("```")
      lines.append("")

  by_tf = exp.get("by_timeframe") or []
  if by_tf:
    lines.extend([
      "## Expectancy by timeframe",
      "",
      "| TF | n | WR | Expectancy R | Gate |",
      "|----|---|-----|--------------|------|",
    ])
    for row in by_tf:
      gate = "✓" if row.get("passes_gate") else "✗"
      wr = row.get("win_rate")
      wr_s = f"{wr:.1%}" if wr is not None else "—"
      lines.append(
        f"| {row.get('slice')} | {row.get('n')} | {wr_s} | {row.get('expectancy_r')} | {gate} |"
      )
    lines.append("")

  lines.extend([
    f"> Tear sheet: `{cost.get('html_report', 'n/a')}`",
    f"> State: `{_state_json_path()}`",
    "",
  ])
  text = "\n".join(lines) + "\n"
  path.write_text(text, encoding="utf-8")
  return text


def run_profit_lab(
  *,
  run_sweep: bool = True,
  run_cpcv: bool = True,
  run_cost: bool = True,
  write_reports: bool = True,
  apply_expectancy_gates: bool = True,
) -> Dict[str, Any]:
  """
  Full profit laboratory tick:
  1. Fee-adjusted returns from tracked setups
  2. Slice expectancy + auto-block state
  3. CPCV / PSR / DSR audit
  4. Cost analytics + quantstats HTML
  5. vectorbt parameter sweep (optional)
  """
  from engine.profit_lab.cost_analytics import run_cost_analytics
  from engine.profit_lab.cpcv_audit import run_cpcv_audit
  from engine.profit_lab.expectancy import build_expectancy_report, save_expectancy_state
  from engine.profit_lab.setup_returns import setups_to_returns_frame
  from engine.profit_lab.vectorbt_sweep import run_vectorbt_sweep

  result: Dict[str, Any] = {"timestamp_utc": _utcnow(), "ok": False}
  # Analyze full history — do not apply live policy/expectancy blocks to the sample (avoids circular filtering).
  df = setups_to_returns_frame(apply_policy=False)

  expectancy = build_expectancy_report(df)
  result["expectancy"] = expectancy
  if apply_expectancy_gates:
    save_expectancy_state(expectancy)

  cpcv: Dict[str, Any] = {"skipped": True}
  if run_cpcv:
    cpcv = run_cpcv_audit(df)
  result["cpcv"] = cpcv

  cost: Dict[str, Any] = {"skipped": True}
  if run_cost and not df.empty:
    cost = run_cost_analytics(
      df["net_r"].tolist(),
      dates=df["datetime"].tolist(),
      write_html=write_reports,
    )
  result["cost_analytics"] = cost

  sweep: Dict[str, Any] = {"skipped": True}
  if run_sweep:
    sweep = run_vectorbt_sweep()
  result["vectorbt_sweep"] = sweep

  # Apply recommended env from sweep if better than current
  if sweep.get("ok") and sweep.get("recommended_env"):
    best = sweep.get("best") or {}
    if best.get("expectancy_r", -999) > (expectancy.get("overall") or {}).get("expectancy_r", -999):
      result["sweep_improves_overall"] = True
      rec = sweep["recommended_env"]
      if rec.get("EW_BLOCKED_TFS") and os.environ.get("EW_PROFIT_LAB_AUTO_APPLY", "0") == "1":
        os.environ["EW_BLOCKED_TFS"] = rec["EW_BLOCKED_TFS"]
      result["recommended_env"] = rec

  readiness = composite_verdict(
    expectancy=expectancy,
    cpcv=cpcv,
    cost=cost,
    sweep=sweep if sweep.get("ok") else None,
  )
  result["readiness"] = readiness
  result["ok"] = readiness["verdict"] != "PROFIT_NO_GO"

  if write_reports:
    write_profit_lab_report(result)
    state_path = _state_json_path()
    state_path.parent.mkdir(parents=True, exist_ok=True)
    state_path.write_text(json.dumps(result, indent=2, default=str), encoding="utf-8")

  return result
