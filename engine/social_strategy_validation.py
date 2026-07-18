"""
Social strategy validation — question forum hype, cross-check measured lift,
and route through multi-AI executive consensus before promoting signals.
"""

from __future__ import annotations

import json
import os
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, List, Optional


VALIDATION_STATE = Path(
  os.environ.get("EW_SOCIAL_VALIDATION_STATE", "output/system/social_strategy_validation.json")
)


def social_validation_enabled() -> bool:
  return os.environ.get("EW_SOCIAL_VALIDATION", "1").lower() not in ("0", "false", "no")


def _build_validation_prompt(
  candidates: List[dict],
  *,
  symbol: str = "",
  direction: str = "",
  impact: Optional[dict] = None,
) -> str:
  lines = [
    "SOCIAL STRATEGY EXECUTIVE VALIDATION",
    "Question every popular forum/CT strategy skeptically before we promote it.",
    "Respond JSON: {\"stance\":\"agree|caution|reject\",\"summary\":\"...\",",
    "\"validated\":[\"strategy_id\"],\"rejected\":[\"strategy_id\"],\"actions\":[\"...\"]}",
    "",
    "RULES:",
    "- agree → promote 1-2 strategies with measured lift + social heat",
    "- caution → paper-test only; do not change sizing",
    "- reject → block social narrative from overriding EW honesty gates",
    "- Never add indicators without measured lift in our closed setups",
    "",
  ]
  if symbol:
    lines.append(f"CONTEXT: {symbol} {direction or 'any direction'}")
  if impact:
    disc = impact.get("discovery") or {}
    lines.append(f"OUR BASELINE WR: {disc.get('baseline_wr', 'n/a')} (n={disc.get('sample_size', 0)})")
    boosts = disc.get("top_boosts") or []
    if boosts:
      lines.append("MEASURED EDGES (trust these over social hype):")
      for b in boosts[:4]:
        lines.append(f"  - {b['factor']}: lift {b.get('lift_vs_baseline', 0):+.1%} n={b.get('n')}")

  lines.extend(["", "FORUM/SOCIAL CANDIDATES TO VALIDATE:"])
  for c in candidates[:8]:
    lines.append(
      f"  [{c.get('validation_prior', '?')}] {c['id']}: {c['name']}"
      f" | heat={c.get('social_heat', 0)} mentions={c.get('mention_count', 0)}"
      f" | measured_lift={c.get('measured_lift', 'n/a')}"
    )
    lines.append(f"    SKEPTIC Q: {c.get('skeptic_q', '')}")

  lines.extend([
    "",
    "QUESTION: Which social strategies deserve promotion vs rejection?",
    "Prioritize strategies that align with our measured edges (bear_impulse_5, SHORT, etc.)",
    "and reject those that contradict our data (bull_impulse_5, 1w probe traps).",
  ])
  return "\n".join(lines)


def _rule_based_validation(candidates: List[dict]) -> Dict[str, Any]:
  """Offline validation when LLM unavailable — skeptical, data-first."""
  validated: List[str] = []
  rejected: List[str] = []
  caution: List[str] = []

  for c in candidates:
    prior = c.get("validation_prior", "low_priority")
    lift = c.get("measured_lift")
    if prior == "likely_valid" or (lift is not None and lift > 0.08):
      validated.append(c["id"])
    elif prior == "likely_noise" or (lift is not None and lift < -0.05):
      rejected.append(c["id"])
    elif c.get("social_heat", 0) >= 30:
      caution.append(c["id"])
    else:
      caution.append(c["id"])

  if validated:
    stance = "agree"
    summary = f"Promote {len(validated)} strategies with measured lift: {', '.join(validated[:3])}"
  elif len(rejected) > len(validated):
    stance = "caution"
    summary = f"Reject social hype on {len(rejected)} strategies; maintain EW-first posture"
  else:
    stance = "caution"
    summary = "No social strategy clears measured-lift bar — paper-test only"

  actions = []
  if validated:
    actions.append(f"Wire validated signals into impact registry: {validated[0]}")
  if rejected:
    actions.append(f"Block narrative override from: {rejected[0]}")
  actions.append("Re-validate after next 50 closed setups")

  return {
    "stance": stance,
    "summary": summary,
    "validated": validated[:5],
    "rejected": rejected[:5],
    "caution": caution[:5],
    "actions": actions,
  }


def run_social_strategy_validation(
  *,
  symbol: str = "",
  direction: str = "",
  use_llm: bool = False,
) -> Dict[str, Any]:
  """
  Full validation pass: discover → question → executive consensus → persist.
  """
  if not social_validation_enabled():
    return {"skipped": True, "reason": "EW_SOCIAL_VALIDATION disabled"}

  from gateway.social_intel import build_social_intel

  impact: dict = {}
  try:
    from engine.impact_discovery import load_impact_report

    impact = load_impact_report()
  except Exception:
    pass

  social = build_social_intel(symbol)
  candidates = social.get("candidates") or []
  prompt = _build_validation_prompt(candidates, symbol=symbol, direction=direction, impact=impact)
  panel = _rule_based_validation(candidates)

  if use_llm:
    try:
      from engine.brain_consensus import ask_brain, brain_consensus_enabled, record_decision

      if brain_consensus_enabled():
        os.environ["EW_BRAIN_PROMPT"] = prompt
        brain = ask_brain(
          "Validate forum/social strategies against our measured outcomes — promote or reject?",
          use_llm=True,
          search_memory=True,
        )
        stance = brain.get("stance") or brain.get("panel", {}).get("consensus_stance", "caution")
        panel = {
          "stance": stance,
          "summary": brain.get("answer") or brain.get("panel", {}).get("blended_summary", panel["summary"]),
          "validated": panel.get("validated", []),
          "rejected": panel.get("rejected", []),
          "caution": panel.get("caution", []),
          "actions": panel.get("actions", []),
          "panel": brain.get("panel"),
          "okf": brain.get("okf"),
        }
        record_decision(
          domain="social_strategy",
          subject=symbol or "GLOBAL",
          verdict=stance,
          stance=stance,
          panel=brain.get("panel") or {},
          context={"candidates": [c["id"] for c in candidates[:8]]},
        )
    except Exception as exc:
      panel["llm_error"] = str(exc)

  result = {
    "timestamp_utc": datetime.now(timezone.utc).isoformat(),
    "symbol": symbol or None,
    "direction": direction or None,
    "consensus_stance": panel.get("stance", "caution"),
    "summary": panel.get("summary", ""),
    "validated_strategies": panel.get("validated", []),
    "rejected_strategies": panel.get("rejected", []),
    "caution_strategies": panel.get("caution", []),
    "actions": panel.get("actions", []),
    "candidates_reviewed": len(candidates),
    "social_mode": social.get("mode"),
    "top_candidates": [
      {
        "id": c["id"],
        "name": c["name"],
        "social_heat": c.get("social_heat"),
        "measured_lift": c.get("measured_lift"),
        "validation_prior": c.get("validation_prior"),
        "skeptic_q": c.get("skeptic_q"),
      }
      for c in candidates[:8]
    ],
    "panel": panel.get("panel"),
  }

  _save_state(result)
  _persist_okf_lesson(result)
  return result


def _save_state(result: dict) -> None:
  VALIDATION_STATE.parent.mkdir(parents=True, exist_ok=True)
  VALIDATION_STATE.write_text(json.dumps(result, indent=2, default=str), encoding="utf-8")


def _persist_okf_lesson(result: dict) -> None:
  try:
    from engine.brain_self_improve import persist_lesson, self_improve_enabled

    if not self_improve_enabled():
      return
    stance = result.get("consensus_stance", "caution")
    validated = result.get("validated_strategies") or []
    rejected = result.get("rejected_strategies") or []
    persist_lesson(
      "GLOBAL",
      f"social_validation {stance}: validated={validated[:2]} rejected={rejected[:2]}",
      source="social_strategy_validation",
    )
  except Exception:
    pass


def load_social_validation() -> dict:
  if not VALIDATION_STATE.exists():
    return {}
  try:
    return json.loads(VALIDATION_STATE.read_text(encoding="utf-8"))
  except (json.JSONDecodeError, OSError):
    return {}
