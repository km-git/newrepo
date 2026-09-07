"""
Continuous proof loop — learn from outcomes, refresh paper policy, run forward tick.

LLM-free cycle for autonomous improvement without score theater.
"""

from __future__ import annotations

import json
import os
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, Optional

REPORT_PATH = Path(os.environ.get("EW_CONTINUOUS_PROOF_REPORT", "reports/CONTINUOUS_PROOF.md"))
CYCLE_LOG = Path(os.environ.get("EW_CONTINUOUS_PROOF_LOG", "output/autonomous/continuous_proof.jsonl"))


def _report_path() -> Path:
  return Path(os.environ.get("EW_CONTINUOUS_PROOF_REPORT", str(REPORT_PATH)))


def _cycle_log_path() -> Path:
  return Path(os.environ.get("EW_CONTINUOUS_PROOF_LOG", str(CYCLE_LOG)))


def _utcnow() -> str:
  return datetime.now(timezone.utc).isoformat()


def _append_cycle(entry: dict) -> None:
  path = _cycle_log_path()
  path.parent.mkdir(parents=True, exist_ok=True)
  with path.open("a", encoding="utf-8") as f:
    f.write(json.dumps(entry, default=str) + "\n")


def run_continuous_proof_cycle(
  *,
  fetch_ohlc: bool = True,
  equity_usd: Optional[float] = None,
  skip_learning: bool = False,
) -> Dict[str, Any]:
  """
  One improvement cycle (no LLM):
  1. Resolve tracked setup outcomes → metrics
  2. Learn paper symbol policy from trade history
  3. Paper-forward tick (OHLC sim + ledger snapshot)
  4. Record cycle summary + report
  """
  os.environ.setdefault("EW_IMPROVEMENT_LLM", "0")
  os.environ.setdefault("EW_GATEWAY_QUIET", "1")
  os.environ.setdefault("EW_FETCH_QUIET", "1")

  result: Dict[str, Any] = {"timestamp_utc": _utcnow(), "phases": {}}

  if skip_learning:
    result["phases"]["outcomes"] = {"skipped": True}
  else:
    try:
      from engine.outcome_tracker import run_learning_phase

      result["phases"]["outcomes"] = run_learning_phase(is_crypto=True)
    except Exception as exc:
      result["phases"]["outcomes"] = {"error": str(exc)}

  try:
    from engine.paper_policy import refresh_paper_policy

    result["phases"]["policy"] = refresh_paper_policy()
  except Exception as exc:
    result["phases"]["policy"] = {"error": str(exc)}

  try:
    from engine.paper_forward_tracker import run_paper_forward_tick

    tick = run_paper_forward_tick(
      fetch_ohlc=fetch_ohlc,
      equity_usd=equity_usd,
      include_effectiveness=False,
    )
    result["phases"]["paper_forward"] = tick
    result["proof"] = tick.get("proof")
  except Exception as exc:
    result["phases"]["paper_forward"] = {"error": str(exc)}
    result["proof"] = None

  proof = result.get("proof") or {}
  metrics = (proof.get("metrics") or {}) if isinstance(proof, dict) else {}
  policy = result["phases"].get("policy") or {}

  result["summary"] = {
    "verdict": proof.get("verdict") if isinstance(proof, dict) else None,
    "cumulative_pnl_usd": metrics.get("cumulative_pnl_usd"),
    "days_recorded": metrics.get("days"),
    "win_rate": metrics.get("win_rate"),
    "blocked_symbols": policy.get("block_symbols") if isinstance(policy, dict) else [],
    "promote_symbols": policy.get("promote_symbols") if isinstance(policy, dict) else [],
    "simulated_today": (
      (result.get("phases") or {}).get("paper_forward", {})
      .get("phases", {})
      .get("paper", {})
      .get("simulated")
    ),
  }

  write_continuous_report(result)
  _append_cycle(result)
  result["ok"] = bool(result["phases"].get("paper_forward"))
  return result


def write_continuous_report(cycle: dict, path: Optional[Path] = None) -> str:
  path = path or _report_path()
  path.parent.mkdir(parents=True, exist_ok=True)
  summary = cycle.get("summary") or {}
  proof = cycle.get("proof") or {}

  cum_pnl = summary.get("cumulative_pnl_usd")
  cum_pnl_str = f"${float(cum_pnl):,.2f}" if cum_pnl is not None else "n/a"

  lines = [
    "# Continuous Proof Cycle",
    "",
    f"**Run:** {cycle.get('timestamp_utc', '')}  ",
    f"**Verdict:** `{summary.get('verdict', 'n/a')}`  ",
    "",
    "## Scoreboard",
    "",
    "| Metric | Value |",
    "|--------|-------|",
    f"| Cumulative P&L | {cum_pnl_str} |",
    f"| Days recorded | {summary.get('days_recorded', 0)} |",
    f"| Paper win rate | {summary.get('win_rate', 'n/a')} |",
    "",
    "## Learned policy",
    "",
    f"**Block:** {', '.join(summary.get('blocked_symbols') or []) or 'none'}  ",
    f"**Promote:** {', '.join(summary.get('promote_symbols') or []) or 'none'}  ",
    "",
    "## Proof gates",
    "",
  ]

  for g in proof.get("gates") or []:
    mark = "✓" if g.get("passed") else "✗"
    lines.append(f"- {g.get('gate')}: {mark} — {g.get('detail')}")

  outcomes = (cycle.get("phases") or {}).get("outcomes") or {}
  if isinstance(outcomes, dict) and outcomes.get("overall"):
    ov = outcomes["overall"]
    lines.extend([
      "",
      "## Outcome tracker",
      "",
      f"- Decided: {ov.get('decided', 'n/a')} · WR: {ov.get('win_rate', 'n/a')}",
    ])

  lines.extend([
    "",
    "> LLM-free loop · `scripts/run_continuous_proof_loop.sh`",
    f"> Cycle log: `{_cycle_log_path()}`",
  ])
  text = "\n".join(lines) + "\n"
  path.write_text(text, encoding="utf-8")
  return text
