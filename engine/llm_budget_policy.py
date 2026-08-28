"""Cheap-first LLM budget policy — ~95% Cursor Pro (Composer/Grok), Other Models gated."""

from __future__ import annotations

import os
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
  Default on — route ~95% of calls to Cursor Pro (Composer/Grok).
  Blocks GPT/Claude/Gemini API slots unless EW_ALLOW_OTHER_MODELS=1.
  """
  raw = os.environ.get("EW_CURSOR_PRO_ONLY", "").lower().strip()
  if raw in ("0", "false", "no"):
    return False
  if raw in ("1", "true", "yes"):
    return True
  return cheap_first_enabled()


def other_models_allowed() -> bool:
  """Explicit opt-in to burn Other Models quota (GPT/Claude/Gemini API)."""
  return os.environ.get("EW_ALLOW_OTHER_MODELS", "0").lower() in ("1", "true", "yes")


def cheap_target_pct() -> int:
  try:
    return max(50, min(99, int(os.environ.get("EW_LLM_CHEAP_TARGET_PCT", "95"))))
  except (TypeError, ValueError):
    return 95


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


def resolve_to_cursor_pro(model_id: str, *, task: str = "") -> str:
  """
  Substitute Other-Models-quota models with Cursor Pro equivalents.
  No-op when other_models_allowed() or model is already Cursor Pro.
  """
  if not model_id or is_cursor_pro_model(model_id):
    return model_id
  if other_models_allowed() and not cursor_pro_only():
    return model_id
  if other_models_allowed() and not is_other_quota_model(model_id):
    return model_id

  if cursor_pro_only() or (cheap_first_enabled() and not other_models_allowed()):
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
  if cursor_pro_only() and not other_models_allowed():
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
  # Cursor Pro mode: never escalate to Other Models — use Grok High instead.
  if cursor_pro_only() and not other_models_allowed():
    return False

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
  if cursor_pro_only() and not other_models_allowed():
    return os.environ.get("EW_LLM_INTELLIGENCE", "dual")
  return os.environ.get("EW_LLM_INTELLIGENCE", "ensemble")


def use_cursor_api_pool() -> bool:
  """API-pool models (GPT/Claude/Gemini) — off by default to protect Other Models quota."""
  if other_models_allowed():
    return True
  return os.environ.get("EW_USE_CURSOR_API_POOL", "0").lower() in ("1", "true", "yes")


def budget_policy_summary() -> Dict[str, Any]:
  return {
    "cheap_first": cheap_first_enabled(),
    "cursor_pro_only": cursor_pro_only(),
    "other_models_allowed": other_models_allowed(),
    "cheap_target_pct": cheap_target_pct(),
    "cursor_pro_models": sorted(CURSOR_PRO_MODELS),
    "routine_mode": routine_intelligence_mode(),
    "executive_mode": executive_intelligence_mode(),
    "use_cursor_api_pool": use_cursor_api_pool(),
    "premium_tasks": sorted(PREMIUM_TASKS),
    "rules": [
      f"~{cheap_target_pct()}% of LLM calls use Cursor Pro (Composer, Grok, Grok High)",
      "EW_CURSOR_PRO_ONLY=1 — Other Models (GPT/Claude/Gemini) blocked unless EW_ALLOW_OTHER_MODELS=1",
      "Executive/self-improvement tiebreaker → cursor-grok-4.5-high (Pro pool), not Opus/Sol",
      "EW_LLM_EW_BYPASS=1 — zero tokens when EW engines strongly agree",
      "tiktoken + tokenpruner + diskcache + zstd — prompt compression + cache",
      "EW_LLM_MAX_TOKENS_PER_MODEL=10000 — per-model daily cap",
    ],
  }
