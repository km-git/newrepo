"""Cheap-first LLM budget policy — ~98% Cursor Pro (Composer/Grok), 2% Other Models (executive only)."""

from __future__ import annotations

import os
from datetime import date
from typing import Any, Dict, List, Literal, Optional

LLMContext = Literal["routine", "executive", "self_improvement"]

PREMIUM_TASKS = frozenset({"executive", "architect", "synthesis"})
STANDARD_ESCALATION_TASKS = frozenset({"tiebreaker", "planning", "review"})
PREMIUM_ROSTER_TIERS = frozenset({"crucial", "flagship"})

# Cursor Pro pool — included in subscription, does NOT consume "Other Models" quota.
CURSOR_PRO_MODELS = frozenset({
  "composer-2.5",
  "grok-4.5",
  "cursor-grok-4.5-high",
})

CURSOR_PRO_DEFAULTS = {
  "workhorse": "composer-2.5",
  "screen_alt": "grok-4.5",
  "reasoning": "cursor-grok-4.5-high",
  "tiebreaker": "cursor-grok-4.5-high",
  "executive_substitute": "cursor-grok-4.5-high",
}


def cheap_first_enabled() -> bool:
  return os.environ.get("EW_CHEAP_FIRST", "1").lower() not in ("0", "false", "no")


def cursor_pro_only() -> bool:
  """
  Default on — route ~98% of calls to Cursor Pro (Composer/Grok).
  Other Models only via may_use_other_model() executive gate (2% budget).
  """
  raw = os.environ.get("EW_CURSOR_PRO_ONLY", "").lower().strip()
  if raw in ("0", "false", "no"):
    return False
  if raw in ("1", "true", "yes"):
    return True
  return cheap_first_enabled()


def other_models_override() -> bool:
  """Dev/test override — lifts all gates (not for production daemons)."""
  return os.environ.get("EW_ALLOW_OTHER_MODELS", "0").lower() in ("1", "true", "yes")


def cheap_target_pct() -> int:
  try:
    return max(50, min(99, int(os.environ.get("EW_LLM_CHEAP_TARGET_PCT", "98"))))
  except (TypeError, ValueError):
    return 98


def other_models_budget_pct() -> float:
  """Target share of LLM calls on Other Models quota — executive only (default 2%)."""
  try:
    return max(0.5, min(10.0, float(os.environ.get("EW_OTHER_MODELS_BUDGET_PCT", "2"))))
  except (TypeError, ValueError):
    return 2.0


def other_models_shame_pct() -> float:
  """Hard ceiling — exceeding this blocks all Other Models calls (default 5%)."""
  try:
    return max(other_models_budget_pct(), min(15.0, float(os.environ.get("EW_OTHER_MODELS_SHAME_PCT", "5"))))
  except (TypeError, ValueError):
    return 5.0


def other_models_allowed(
  task: str = "",
  context: LLMContext = "routine",
  verdict: str = "",
  conviction: str = "",
  stances: Optional[List[str]] = None,
) -> bool:
  """True only when executive gate + 2% pool budget permits Other Models."""
  if other_models_override() and not cursor_pro_only():
    return True
  return may_use_other_model(task, context, verdict, conviction, stances)


def is_cursor_pro_model(model_id: str) -> bool:
  mid = (model_id or "").strip()
  if mid in CURSOR_PRO_MODELS:
    return True
  m = mid.lower()
  return m.startswith("composer") or m.startswith("grok") or "cursor-grok" in m


def is_other_quota_model(model_id: str) -> bool:
  """Models that consume Cursor 'Other Models' quota (not Pro pool)."""
  if not model_id or is_cursor_pro_model(model_id):
    return False
  m = model_id.lower()
  if m.startswith("gpt-"):
    return True
  if m.startswith("claude-"):
    return True
  if m.startswith("gemini-"):
    return True
  if "opus" in m or "fable" in m or "sonnet" in m:
    return True
  return False


def _pool_tracker():
  from engine.llm_token_saver import get_pool_mix_tracker

  return get_pool_mix_tracker()


def may_use_other_model(
  task: str = "",
  context: LLMContext = "routine",
  verdict: str = "",
  conviction: str = "",
  stances: Optional[List[str]] = None,
) -> bool:
  """
  Strict gate for the 2% Other Models budget — executive decision-making ONLY.
  Requires: task=executive, context=executive, hard disagreement, GO, high conviction.
  Blocks at 2% budget; hard-blocks at 5% shame threshold.
  """
  if task != "executive" or context != "executive":
    return False

  sev = _disagreement_severity(stances or [])
  v = str(verdict or "").upper()
  conv = str(conviction or "").lower()
  if not (sev == "hard" and v == "GO" and conv == "high"):
    return False

  tracker = _pool_tracker()
  if tracker.at_shame_limit():
    return False
  if tracker.at_budget_limit():
    return False
  return True


def resolve_to_cursor_pro(
  model_id: str,
  *,
  task: str = "",
  context: LLMContext = "routine",
  verdict: str = "",
  conviction: str = "",
  stances: Optional[List[str]] = None,
) -> str:
  """
  Substitute Other-Models-quota models with Cursor Pro equivalents.
  Passthrough only when may_use_other_model() approves (executive + 2% budget).
  """
  if not model_id or is_cursor_pro_model(model_id):
    return model_id
  if other_models_override() and not cursor_pro_only():
    return model_id
  if may_use_other_model(task, context, verdict, conviction, stances):
    return model_id

  if cursor_pro_only() or cheap_first_enabled():
    if task in ("executive", "architect", "synthesis") or model_id in (
      os.environ.get("EW_MODEL_OPUS", "claude-opus-4-8"),
      os.environ.get("EW_MODEL_FABLE", "claude-fable-5"),
      os.environ.get("EW_MODEL_SOL", "gpt-5.6-sol"),
    ):
      return os.environ.get("EW_MODEL_GROK_HIGH", CURSOR_PRO_DEFAULTS["executive_substitute"])
    if "mini" in model_id.lower() or "nano" in model_id.lower():
      return os.environ.get("EW_MODEL_WORKHORSE_FP", CURSOR_PRO_DEFAULTS["workhorse"])
    if task in ("tiebreaker", "planning", "review"):
      return os.environ.get("EW_MODEL_GROK_HIGH", CURSOR_PRO_DEFAULTS["tiebreaker"])
    return os.environ.get("EW_MODEL_GROK_HIGH", CURSOR_PRO_DEFAULTS["reasoning"])

  return model_id


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
  if cursor_pro_only() and not other_models_allowed(task=task, context=context):
    return context != "routine" and task == "tiebreaker"
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
  # Other Models: executive decision-making only, within 2% pool.
  if task == "executive" and context == "executive":
    return may_use_other_model(task, context, verdict, conviction, stances)

  if cursor_pro_only():
    return False

  if not cheap_first_enabled():
    return True
  if task not in PREMIUM_TASKS and not is_premium_model(task):
    return allow_standard_escalation(task, context=context)

  # Non-executive premium (architect/synthesis/self-improvement) — Cursor Pro only.
  return False


def routine_intelligence_mode() -> str:
  if not cheap_first_enabled():
    return os.environ.get("EW_LLM_INTELLIGENCE", "ensemble")
  return os.environ.get("EW_LLM_ROUTINE_INTELLIGENCE", "single")


def executive_intelligence_mode() -> str:
  return os.environ.get("EW_LLM_INTELLIGENCE", "dual")


def use_cursor_api_pool() -> bool:
  """API-pool models — never on by default; protect Other Models quota."""
  if other_models_override() and not cursor_pro_only():
    return True
  return os.environ.get("EW_USE_CURSOR_API_POOL", "0").lower() in ("1", "true", "yes")


def pool_mix_summary() -> Dict[str, Any]:
  return _pool_tracker().summary(
    budget_pct=other_models_budget_pct(),
    shame_pct=other_models_shame_pct(),
    target_pct=cheap_target_pct(),
  )


def budget_policy_summary() -> Dict[str, Any]:
  mix = pool_mix_summary()
  return {
    "cheap_first": cheap_first_enabled(),
    "cursor_pro_only": cursor_pro_only(),
    "other_models_override": other_models_override(),
    "cheap_target_pct": cheap_target_pct(),
    "other_models_budget_pct": other_models_budget_pct(),
    "other_models_shame_pct": other_models_shame_pct(),
    "cursor_pro_models": sorted(CURSOR_PRO_MODELS),
    "routine_mode": routine_intelligence_mode(),
    "executive_mode": executive_intelligence_mode(),
    "use_cursor_api_pool": use_cursor_api_pool(),
    "premium_tasks": sorted(PREMIUM_TASKS),
    "pool_mix": mix,
    "rules": [
      f"~{cheap_target_pct()}% of LLM calls use Cursor Pro (Composer, Grok, Grok High)",
      f"≤{other_models_budget_pct()}% Other Models — executive GO+high conviction ONLY",
      f"≥{other_models_shame_pct()}% Other Models — hard block (shame threshold)",
      "Routine/tiebreaker/planning/PR/improvement → Cursor Pro only (Grok High / Composer)",
      "EW_ALLOW_OTHER_MODELS=1 + EW_CURSOR_PRO_ONLY=0 — dev override only",
      "EW_LLM_EW_BYPASS=1 — zero tokens when EW engines strongly agree",
      "tiktoken + tokenpruner + diskcache + zstd — prompt compression + cache",
      "EW_LLM_MAX_TOKENS_PER_MODEL=10000 — per-model daily cap",
    ],
  }
