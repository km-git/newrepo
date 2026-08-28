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


def _build_review_prompt(metrics: dict, tv_summary: dict, impact: Optional[dict] = None, social: Optional[dict] = None, tv_oss: Optional[dict] = None) -> str:
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
  ])
  if impact:
    lines.extend([
      "",
      "IMPACT DISCOVERY (hidden factors):",
      f"baseline_wr={impact.get('discovery', {}).get('baseline_wr')}",
      "top_boosts: " + ", ".join(
        f"{b['factor']}({b.get('lift_vs_baseline', 0):+.1%})"
        for b in impact.get("discovery", {}).get("top_boosts", [])[:5]
      ),
      "recommendations: " + "; ".join(impact.get("recommendations", [])[:4]),
    ])
  if social and not social.get("skipped"):
    lines.extend([
      "",
      "SOCIAL STRATEGY VALIDATION (forum/CT executive review):",
      f"stance={social.get('consensus_stance')} validated={social.get('validated_strategies', [])[:3]}",
      f"rejected={social.get('rejected_strategies', [])[:3]}",
      f"summary: {(social.get('summary') or '')[:300]}",
    ])
  if tv_oss and not tv_oss.get("skipped"):
    lines.extend([
      "",
      "TV OSS COMPLEMENTARY STACK (TradingView open-source):",
      f"active={tv_oss.get('active_indicators', [])}",
      f"layer_weights={tv_oss.get('layer_weights', {})}",
      f"summary: {(tv_oss.get('summary') or '')[:300]}",
    ])
  lines.extend([
    "",
    "QUESTION: Given historical outcomes and TV indicator alignment data,",
    "should we tighten risk (reduce probe size), maintain, or allow selective boost?",
    "List 1-3 concrete actions. Prioritize hidden high-lift factors over adding more indicators.",
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
    "tv_filters": [
      "cvd", "footprint", "volume_profile", "tpo", "anchored_vwap",
      "liquidity_pools", "hidden_liquidity",
      "supertrend", "chandelier", "ttm_squeeze", "adx",
    ],
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
  impact = {}
  try:
    from engine.impact_discovery import run_impact_discovery

    impact = run_impact_discovery()
  except Exception as exc:
    impact = {"error": str(exc)}

  social_validation = {}
  if os.environ.get("EW_SOCIAL_VALIDATION", "1").lower() not in ("0", "false", "no"):
    try:
      from engine.social_strategy_validation import run_social_strategy_validation

      social_validation = run_social_strategy_validation(use_llm=use_llm)
    except Exception as exc:
      social_validation = {"error": str(exc)}

  tv_oss = {}
  if os.environ.get("EW_TV_OSS_CONSENSUS", "1").lower() not in ("0", "false", "no"):
    try:
      from engine.tv_oss_consensus import run_tv_oss_consensus

      tv_oss = run_tv_oss_consensus(use_llm=use_llm)
    except Exception as exc:
      tv_oss = {"error": str(exc)}

  prompt = _build_review_prompt(metrics, tv_summary, impact, social_validation, tv_oss)

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
        brain = ask_brain(
          "Risk executive review: tighten, maintain, or boost probe sizing?",
          use_llm=True,
          search_memory=True,
          context=prompt,
        )
        panel = {
          "consensus_stance": brain.get("stance") or brain.get("panel", {}).get("consensus_stance", "caution"),
          "blended_summary": brain.get("answer") or brain.get("panel", {}).get("blended_summary", ""),
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
    "impact_discovery": impact.get("recommendations", []) if isinstance(impact, dict) else [],
    "social_validation": social_validation.get("summary") if isinstance(social_validation, dict) else None,
    "social_validated": social_validation.get("validated_strategies", []) if isinstance(social_validation, dict) else [],
    "tv_oss_active": tv_oss.get("active_indicators", []) if isinstance(tv_oss, dict) else [],
    "tv_oss_weights": tv_oss.get("layer_weights") if isinstance(tv_oss, dict) else {},
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
