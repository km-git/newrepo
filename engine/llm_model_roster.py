"""Cursor model roster — every model assigned by strength, pool, and token budget."""

from __future__ import annotations

import os
from typing import Any, Dict, List, Literal, Optional, Tuple

from engine.llm_gpt_policy import gpt_replacement_for, minimize_gpt_enabled

ModelTier = Literal["nano", "workhorse", "standard", "crucial", "flagship"]
ModelPool = Literal["first_party", "api"]
DisagreementSeverity = Literal["none", "mild", "hard"]


def _m(key: str, default: str) -> str:
  return os.environ.get(key, default)


ROSTER: Dict[str, Dict[str, Any]] = {
  "composer-2.5": {
    "tier": "workhorse",
    "pool": "first_party",
    "family": "cursor",
    "strength": "Fast agentic screen — cheapest Pro pool",
  },
  "grok-4.5": {
    "tier": "workhorse",
    "pool": "first_party",
    "family": "cursor",
    "strength": "Alt screen — long-context reasoning",
  },
  "cursor-grok-4.5-high": {
    "tier": "standard",
    "pool": "first_party",
    "family": "cursor",
    "strength": "Cursor Grok High — reasoning screen, mild tiebreaker",
  },
  "gpt-5.4-nano": {
    "tier": "nano",
    "pool": "api",
    "family": "openai",
    "strength": "High-volume cheap screen — budget-limited",
  },
  "gpt-5-mini": {
    "tier": "workhorse",
    "pool": "api",
    "family": "openai",
    "strength": "Dual screen slot B — budget-limited",
  },
  "gpt-5.6-luna": {
    "tier": "standard",
    "pool": "api",
    "family": "openai",
    "strength": "Light planning — CONDITIONAL_GO",
  },
  "gpt-5.6-terra": {
    "tier": "standard",
    "pool": "api",
    "family": "openai",
    "strength": "Mild tiebreaker when Grok High disabled",
  },
  "gpt-5.6-sol": {
    "tier": "crucial",
    "pool": "api",
    "family": "openai",
    "strength": "Hard disagreement + full planning — budget-limited",
  },
  "claude-4.5-sonnet": {
    "tier": "standard",
    "pool": "api",
    "family": "anthropic",
    "strength": "Balanced review — mid premium",
  },
  "claude-opus-4-8": {
    "tier": "flagship",
    "pool": "api",
    "family": "anthropic",
    "strength": "Executive GO + hard disagreement",
  },
  "claude-fable-5": {
    "tier": "flagship",
    "pool": "api",
    "family": "anthropic",
    "strength": "Architect / synthesis",
  },
  "gemini-3-flash": {
    "tier": "workhorse",
    "pool": "api",
    "family": "google",
    "strength": "Optional alt screen",
  },
}

MODEL = {
  "nano": gpt_replacement_for("nano", _m("EW_MODEL_NANO", "gpt-5.4-nano")),
  "workhorse_fp": _m("EW_MODEL_WORKHORSE_FP", "composer-2.5"),
  "workhorse_api": gpt_replacement_for("workhorse_api", _m("EW_MODEL_WORKHORSE_API", "gpt-5-mini")),
  "grok_high": _m("EW_MODEL_GROK_HIGH", "cursor-grok-4.5-high"),
  "screen_a": _m("EW_MODEL_SCREEN_A", "cursor-grok-4.5-high"),
  "screen_b": gpt_replacement_for("screen_b", _m("EW_MODEL_SCREEN_B", "gpt-5-mini")),
  "screen_alt": _m("EW_MODEL_SCREEN_ALT", "grok-4.5"),
  "screen_c": _m("EW_MODEL_SCREEN_C", "gemini-3-flash"),
  "review": _m("EW_MODEL_REVIEW", "cursor-grok-4.5-high"),
  "mild_tb": gpt_replacement_for("mild_tb", _m("EW_MODEL_MILD_TB", "gpt-5.6-terra")),
  "light_plan": gpt_replacement_for("light_plan", _m("EW_MODEL_LIGHT_PLAN", "gpt-5.6-luna")),
  "sol": gpt_replacement_for("sol", _m("EW_MODEL_SOL", "gpt-5.6-sol")),
  "opus": _m("EW_MODEL_OPUS", "claude-opus-4-8"),
  "fable": _m("EW_MODEL_FABLE", "claude-fable-5"),
}


def grok_high_enabled() -> bool:
  return os.environ.get("EW_USE_GROK_HIGH", "1").lower() not in ("0", "false", "no")


def grok_high_model() -> str:
  return MODEL["grok_high"]


def mild_tb_model() -> str:
  """Runtime mild tiebreaker — respects EW_USE_GROK_HIGH and EW_MODEL_MILD_TB."""
  if grok_high_enabled():
    return grok_high_model()
  if minimize_gpt_enabled():
    return gpt_replacement_for("mild_tb", "composer-2.5")
  return _m("EW_MODEL_MILD_TB", "gpt-5.6-terra")


def workhorse_model() -> str:
  """Prefer first-party composer; API workhorse when EW_LLM_WORKHORSE_POOL=api."""
  pool = os.environ.get("EW_LLM_WORKHORSE_POOL", "first_party").lower()
  if pool == "api":
    return MODEL["workhorse_api"]
  return MODEL["workhorse_fp"]


def screen_model_slots() -> List[Tuple[str, str]]:
  """Dual screen — Cursor Pro only by default (95% pool target)."""
  from engine.model_budget_governor import cursor_only_screen, other_model_pool_enabled

  if cursor_only_screen() or not other_model_pool_enabled():
    a = grok_high_model() if grok_high_enabled() else MODEL["workhorse_fp"]
    b = MODEL["workhorse_fp"] if a != MODEL["workhorse_fp"] else MODEL["screen_alt"]
    return [("cursor", a), ("composer", b)]

  if os.environ.get("EW_LLM_SCREEN_DIVERSE", "").lower() in ("1", "true"):
    a = MODEL["screen_alt"]
  elif grok_high_enabled():
    a = grok_high_model()
  else:
    a = MODEL["workhorse_fp"]
  b = MODEL["screen_b"]
  if minimize_gpt_enabled():
    return [("cursor", a), ("composer", b)]
  return [("cursor", a), ("openai", b)]


def disagreement_severity(stances: List[str]) -> DisagreementSeverity:
  if len(stances) < 2:
    return "none"
  unique = set(stances)
  if unique == {"agree"}:
    return "none"
  if "reject" in unique and "agree" in unique:
    return "hard"
  if unique <= {"agree", "caution"}:
    return "mild"
  return "hard"


def escalate_task_model(
  task: str,
  verdict: str = "",
  conviction: str = "",
  stances: Optional[List[str]] = None,
) -> Tuple[str, str, str]:
  from engine.model_budget_governor import (
    prefer_cursor_pool_model,
    purpose_for_brain_domain,
    should_use_other_model,
  )

  sev = disagreement_severity(stances or [])
  purpose = "executive" if task in ("executive", "architect") else "self_improvement"

  if task == "workhorse":
    return workhorse_model(), "workhorse", "composer — cheapest"

  if task == "screen":
    return "", "workhorse", "Grok+Composer parallel — Cursor Pro only"

  if task == "architect":
    model = MODEL["fable"]
    if not should_use_other_model(purpose):
      model, _ = prefer_cursor_pool_model(model, purpose=purpose)
    return model, "flagship" if should_use_other_model(purpose) else "standard", "multi-file deep reasoning"

  if task == "executive":
    model = MODEL["opus"]
    if not should_use_other_model("executive", force_critical=(verdict == "GO" and conviction == "high")):
      model, _ = prefer_cursor_pool_model(model, purpose="executive")
    tier = "flagship" if model == MODEL["opus"] else "standard"
    return model, tier, "GO + high conviction"

  if task == "synthesis":
    model = MODEL["sol"]
    if not should_use_other_model(purpose):
      model, _ = prefer_cursor_pool_model(model, purpose=purpose)
    tier = "crucial" if model == MODEL["sol"] else "standard"
    return model, tier, "Sol synthesis — budget-limited"

  if task == "planning":
    if verdict == "CONDITIONAL_GO" and conviction != "high":
      model = MODEL["light_plan"]
    else:
      model = MODEL["sol"]
    if not should_use_other_model(purpose):
      model, _ = prefer_cursor_pool_model(model, purpose=purpose)
    tier = "standard" if model in (MODEL["light_plan"], MODEL["grok_high"], "cursor-grok-4.5-high") else "crucial"
    reason = "Luna light plan" if verdict == "CONDITIONAL_GO" and conviction != "high" else "Sol full plan"
    return model, tier, reason

  if task in ("tiebreaker", "review"):
    if sev == "mild":
      if grok_high_enabled():
        return grok_high_model(), "standard", "mild — Grok High only"
      return mild_tb_model(), "standard", "mild — Terra fallback"
    if sev == "hard" and verdict == "GO" and conviction == "high":
      model = MODEL["opus"]
      if should_use_other_model("executive", force_critical=True):
        return model, "flagship", "hard disagree executive GO"
      model, _ = prefer_cursor_pool_model(model, purpose="executive", force_critical=True)
      return model, "standard", "hard disagree — Cursor Grok High (Other Models budget)"
    if sev == "hard":
      model = MODEL["sol"]
      if should_use_other_model(purpose):
        return model, "crucial", "hard disagreement — Sol"
      model, _ = prefer_cursor_pool_model(model, purpose=purpose)
      return model, "standard", "hard disagreement — Cursor Grok High"
    if grok_high_enabled():
      return grok_high_model(), "standard", "mid review — Grok High"
    return mild_tb_model(), "standard", "mid review — Terra fallback"

  return workhorse_model(), "workhorse", "fallback composer"


def roster_summary() -> Dict[str, Any]:
  assignments = []
  for task in (
    "workhorse", "screen", "tiebreaker_mild", "tiebreaker",
    "planning_light", "planning", "executive", "architect", "synthesis",
  ):
    if task == "screen":
      slots = screen_model_slots()
      model = " + ".join(m for _, m in slots)
      reason = "Grok High + GPT-mini screen"
      tier = "workhorse"
    elif task == "tiebreaker_mild":
      model, tier, reason = escalate_task_model("tiebreaker", stances=["agree", "caution"])
    elif task == "planning_light":
      model, tier, reason = escalate_task_model("planning", "CONDITIONAL_GO", "medium")
    else:
      base = task.replace("_light", "").replace("_mild", "")
      model, tier, reason = escalate_task_model(base, "GO", "high", ["agree", "reject"])
    assignments.append({"task": task, "model": model, "tier": tier, "reason": reason})

  return {
    "models": {mid: meta for mid, meta in ROSTER.items()},
    "resolved": dict(MODEL),
    "assignments": assignments,
    "efficiency_rules": [
      "EW_LLM_MAX_TOKENS_PER_MODEL=10000 — each model capped independently",
      "EW_LLM_EW_BYPASS=1 — GitHub EW consensus = 0 LLM tokens",
      "tiktoken + llm-token-optimizer + tokenpruner — prompt compression",
      "diskcache + zstandard + cachetic — compressed persistent cache",
      "joblib memoize — deduplicate repeated LLM calls",
      "TokenStore — pipeline logs store hashes not full payloads",
      "per-task output caps: workhorse 120, screen 150",
    ],
  }
