"""
Multi-model executive consensus for risk & continuous improvement.

Uses the brain/panel pattern to review metrics, TV indicator efficacy,
and propose risk parameter adjustments — persisted to OKF.
"""

from __future__ import annotations

import json
import os
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, List, Optional


RISK_STATE_PATH = Path(os.environ.get("EW_RISK_CONSENSUS_STATE", "output/system/risk_consensus.json"))


def risk_consensus_enabled() -> bool:
  return os.environ.get("EW_RISK_CONSENSUS", "1").lower() not in ("0", "false", "no")


def _build_review_prompt(metrics: dict, tv_summary: dict) -> str:
  overall = metrics.get("overall") or {}
  wr = overall.get("win_rate")
  wr_s = f"{wr:.1%}" if wr is not None else "n/a"
  by_tf = metrics.get("by_timeframe") or {}

  lines = [
    "RISK & IMPROVEMENT EXECUTIVE REVIEW",
    "Respond JSON: {\"stance\":\"agree|caution|reject\",\"summary\":\"...\",\"actions\":[\"...\"],\"risk_adjustment\":0.0}",
    "stance=agree → maintain/boost risk; caution → reduce probe sizing; reject → halt new probes",
    "",
    f"GLOBAL: win_rate={wr_s} decided={overall.get('decided',0)} open={metrics.get('open_count',0)}",
    "",
    "BY TIMEFRAME:",
  ]
  for tf, b in by_tf.items():
    twr = b.get("win_rate")
    twr_s = f"{twr:.1%}" if twr is not None else "n/a"
    lines.append(f"  {tf}: wr={twr_s} n={b.get('n',0)}")

  lines.extend([
    "",
    "TV OSS INDICATOR SUMMARY:",
    json.dumps(tv_summary, indent=2)[:2000],
    "",
    "QUESTION: Given historical outcomes and TV indicator alignment data,",
    "should we tighten risk (reduce probe size), maintain, or allow selective boost?",
    "List 1-3 concrete actions.",
  ])
  return "\n".join(lines)


def summarize_tv_efficacy(metrics: dict) -> Dict[str, Any]:
  """
  Heuristic summary of which TFs/styles benefit from TV filters.
  Used as context for multi-model review (no extra API calls).
  """
  by_tf = metrics.get("by_timeframe") or {}
  ranked = []
  for tf, b in by_tf.items():
    wr = b.get("win_rate")
    if wr is None:
      continue
    ranked.append({"tf": tf, "win_rate": wr, "n": b.get("n", 0)})
  ranked.sort(key=lambda x: -x["win_rate"])

  return {
    "best_tf": ranked[0] if ranked else None,
    "worst_tf": ranked[-1] if ranked else None,
    "recommendation": (
      "Favor 4h/15m/1d where win rate >60%; apply Supertrend+ADX filter on 1w (weakest TF)."
      if ranked and ranked[-1].get("win_rate", 1) < 0.52
      else "Maintain current TV filter weights."
    ),
    "tv_filters": ["supertrend", "bollinger_pct_b", "adx_trend"],
    "dynamic_risk": "EW_DYNAMIC_RISK=1 scales size by vol percentile + TV score + history",
  }


def run_risk_consensus(
  metrics: Optional[dict] = None,
  *,
  use_llm: bool = False,
) -> Dict[str, Any]:
  """
  Executive multi-model review of risk posture after learning phase.
  Persists decision to OKF when brain consensus is enabled.
  """
  if not risk_consensus_enabled():
    return {"skipped": True, "reason": "EW_RISK_CONSENSUS disabled"}

  from engine.outcome_tracker import load_metrics

  metrics = metrics or load_metrics()
  tv_summary = summarize_tv_efficacy(metrics)
  prompt = _build_review_prompt(metrics, tv_summary)

  panel: Dict[str, Any] = {
    "consensus_stance": "caution",
    "blended_summary": tv_summary["recommendation"],
    "actions": [
      "Apply Supertrend+ADX gate on 1w probe entries",
      "Reduce size when ATR percentile > 80",
      "Boost +10% on pair×TF with hist win rate > 55%",
    ],
  }

  if use_llm:
    try:
      from engine.brain_consensus import brain_consensus_enabled, ask_brain

      if brain_consensus_enabled():
        os.environ["EW_BRAIN_PROMPT"] = prompt
        brain = ask_brain(
          "Risk executive review: tighten, maintain, or boost probe sizing?",
          use_llm=True,
          search_memory=True,
        )
        panel = {
          "consensus_stance": brain.get("consensus_stance", "caution"),
          "blended_summary": brain.get("blended_summary", ""),
          "panel": brain.get("panel"),
          "okf": brain.get("okf"),
        }
    except Exception as exc:
      panel["llm_error"] = str(exc)

  # Rule-based risk adjustment from global win rate
  overall = metrics.get("overall") or {}
  wr = overall.get("win_rate")
  risk_adj = 0.0
  if wr is not None:
    if wr < 0.50:
      risk_adj = -0.15
      panel["consensus_stance"] = "reject"
    elif wr < 0.58:
      risk_adj = -0.05
      if panel.get("consensus_stance") == "agree":
        panel["consensus_stance"] = "caution"
    elif wr > 0.65:
      risk_adj = 0.05

  result = {
    "timestamp_utc": datetime.now(timezone.utc).isoformat(),
    "consensus_stance": panel.get("consensus_stance"),
    "summary": panel.get("blended_summary"),
    "actions": panel.get("actions", []),
    "risk_adjustment": risk_adj,
    "tv_summary": tv_summary,
    "global_win_rate": wr,
    "panel": panel.get("panel"),
  }

  _save_state(result)
  _persist_okf(result)
  return result


def _save_state(result: dict) -> None:
  RISK_STATE_PATH.parent.mkdir(parents=True, exist_ok=True)
  RISK_STATE_PATH.write_text(json.dumps(result, indent=2, default=str), encoding="utf-8")


def _persist_okf(result: dict) -> None:
  try:
    from engine.brain_self_improve import persist_lesson, self_improve_enabled

    if not self_improve_enabled():
      return
    summary = result.get("summary") or ""
    stance = result.get("consensus_stance", "caution")
    persist_lesson(
      "GLOBAL",
      f"risk_consensus {stance}: {summary[:200]}",
      source="risk_consensus",
    )
  except Exception:
    pass


def load_risk_consensus() -> dict:
  if not RISK_STATE_PATH.exists():
    return {}
  try:
    return json.loads(RISK_STATE_PATH.read_text(encoding="utf-8"))
  except (json.JSONDecodeError, OSError):
    return {}
