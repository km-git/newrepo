"""Cheap-first LLM budget policy — ~90% Cursor workhorse calls, premium only when crucial."""

from __future__ import annotations

import os
from typing import Any, Dict, List, Literal, Optional

LLMContext = Literal["routine", "executive", "self_improvement"]

PREMIUM_TASKS = frozenset({"executive", "architect", "synthesis"})
STANDARD_ESCALATION_TASKS = frozenset({"tiebreaker", "planning", "review"})
PREMIUM_ROSTER_TIERS = frozenset({"crucial", "flagship"})


def cheap_first_enabled() -> bool:
  """Default on — prefer Cursor first-party workhorses; gate premium escalation."""
  return os.environ.get("EW_CHEAP_FIRST", "1").lower() not in ("0", "false", "no")


def cheap_target_pct() -> int:
  try:
    return max(50, min(99, int(os.environ.get("EW_LLM_CHEAP_TARGET_PCT", "90"))))
  except (TypeError, ValueError):
    return 90


def _roster():
  from engine.llm_model_roster import ROSTER

  return ROSTER


def _disagreement_severity(stances: List[str]) -> str:
  from engine.llm_model_roster import disagreement_severity

  return disagreement_severity(stances)


def model_roster_tier(model_id: str) -> str:
  return str((_roster().get(model_id) or {}).get("tier") or "workhorse")


def is_premium_model(model_id: str) -> bool:
  return model_roster_tier(model_id) in PREMIUM_ROSTER_TIERS


def is_premium_task(task: str) -> bool:
  return task in PREMIUM_TASKS


def allow_standard_escalation(
  task: str,
  *,
  context: LLMContext = "routine",
) -> bool:
  if not cheap_first_enabled():
    return True
  if task in ("workhorse", "screen"):
    return False
  if context == "routine":
    return task == "tiebreaker"
  return True


def allow_premium_escalation(
  task: str,
  verdict: str = "",
  conviction: str = "",
  stances: Optional[List[str]] = None,
  *,
  context: LLMContext = "routine",
  metrics_poor: bool = False,
) -> bool:
  if not cheap_first_enabled():
    return True
  if task not in PREMIUM_TASKS and not is_premium_model(task):
    return allow_standard_escalation(task, context=context)

  sev = _disagreement_severity(stances or [])
  v = str(verdict or "").upper()
  conv = str(conviction or "").lower()

  if context == "routine":
    return False

  if context == "self_improvement":
    return sev == "hard" or metrics_poor

  if task == "executive":
    return sev == "hard" and v == "GO" and conv == "high"
  if task == "architect":
    return context == "self_improvement" and (sev == "hard" or metrics_poor)
  if task == "synthesis":
    return sev == "hard" or (v in ("GO", "CONDITIONAL_GO") and conv == "high")
  if task == "planning" and conv == "high":
    return sev == "hard" or v == "GO"

  return False


def routine_intelligence_mode() -> str:
  if not cheap_first_enabled():
    return os.environ.get("EW_LLM_INTELLIGENCE", "ensemble")
  return os.environ.get("EW_LLM_ROUTINE_INTELLIGENCE", "single")


def executive_intelligence_mode() -> str:
  return os.environ.get("EW_LLM_INTELLIGENCE", "ensemble")


def budget_policy_summary() -> Dict[str, Any]:
  return {
    "cheap_first": cheap_first_enabled(),
    "cheap_target_pct": cheap_target_pct(),
    "routine_mode": routine_intelligence_mode(),
    "executive_mode": executive_intelligence_mode(),
    "premium_tasks": sorted(PREMIUM_TASKS),
    "rules": [
      f"~{cheap_target_pct()}% of LLM calls use cheap Cursor workhorses (Composer, Grok, Gemini)",
      "Premium (Opus/Fable/Sol) only for executive GO + hard disagree, or self-improvement hard disagree / poor metrics",
      "EW_LLM_EW_BYPASS=1 — zero tokens when EW engines strongly agree",
      "tiktoken + llm-token-optimizer + tokenpruner + diskcache + zstd — prompt compression + cache",
      "EW_LLM_MAX_TOKENS_PER_MODEL=10000 — per-model daily cap",
      "EW_MINIMIZE_GPT follows EW_CHEAP_FIRST — prefer first-party over GPT API slots",
    ],
  }
