"""Cursor model roster — every model assigned by strength, pool, and token budget."""

from __future__ import annotations

import os
from typing import Any, Dict, List, Literal, Optional, Tuple

ModelTier = Literal["nano", "workhorse", "standard", "crucial", "flagship"]
ModelPool = Literal["first_party", "api"]

# Env overrides for the full roster
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
    "strength": "Cursor Grok High — reasoning screen, mild tiebreaker, light review",
  },
  "gpt-5.4-nano": {
    "tier": "nano",
    "pool": "api",
    "family": "openai",
    "strength": "Ultra-cheap batch workhorse",
  },
  "gpt-5-mini": {
    "tier": "workhorse",
    "pool": "api",
    "family": "openai",
    "strength": "OpenAI cheap screen / JSON",
  },
  "gpt-5.6-luna": {
    "tier": "standard",
    "pool": "api",
    "family": "openai",
    "strength": "Light planning — mid cost",
  },
  "gpt-5.6-terra": {
    "tier": "standard",
    "pool": "api",
    "family": "openai",
    "strength": "Mild disagreement tiebreaker",
  },
  "gpt-5.6-sol": {
    "tier": "crucial",
    "pool": "api",
    "family": "openai",
    "strength": "Planning, synthesis, hard tiebreaker",
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
    "strength": "Executive GO + high conviction",
  },
  "claude-fable-5": {
    "tier": "flagship",
    "pool": "api",
    "family": "anthropic",
    "strength": "Architect — multi-file deep reasoning",
  },
  "gemini-3-flash": {
    "tier": "workhorse",
    "pool": "api",
    "family": "google",
    "strength": "Optional alt screen — Google fast",
  },
}

# Resolved model IDs (override any via EW_MODEL_<slug>)
MODEL = {
  "nano": _m("EW_MODEL_NANO", "gpt-5.4-nano"),
  "workhorse_fp": _m("EW_MODEL_WORKHORSE_FP", "composer-2.5"),
  "workhorse_api": _m("EW_MODEL_WORKHORSE_API", "gpt-5.4-nano"),
  "grok_high": _m("EW_MODEL_GROK_HIGH", "cursor-grok-4.5-high"),
  "screen_a": _m("EW_MODEL_SCREEN_A", "cursor-grok-4.5-high"),
  "screen_b": _m("EW_MODEL_SCREEN_B", "gpt-5-mini"),
  "screen_alt": _m("EW_MODEL_SCREEN_ALT", "grok-4.5"),
  "screen_c": _m("EW_MODEL_SCREEN_C", "gemini-3-flash"),
  "review": _m("EW_MODEL_REVIEW", "claude-4.5-sonnet"),
  "mild_tb": _m("EW_MODEL_MILD_TB", "gpt-5.6-terra"),
  "light_plan": _m("EW_MODEL_LIGHT_PLAN", "gpt-5.6-luna"),
  "sol": _m("EW_MODEL_SOL", "gpt-5.6-sol"),
  "opus": _m("EW_MODEL_OPUS", "claude-opus-4-8"),
  "fable": _m("EW_MODEL_FABLE", "claude-fable-5"),
}

DisagreementSeverity = Literal["none", "mild", "hard"]


def grok_high_enabled() -> bool:
  """Default on — set EW_USE_GROK_HIGH=0 to fall back to composer/Terra/Sonnet."""
  return os.environ.get("EW_USE_GROK_HIGH", "1").lower() not in ("0", "false", "no")


def grok_high_model() -> str:
  return MODEL["grok_high"]


def workhorse_model() -> str:
  """Cheapest path: nano (API) or composer (first-party Pro pool)."""
  pool = os.environ.get("EW_LLM_WORKHORSE_POOL", "first_party").lower()
  if pool == "api":
    return MODEL["workhorse_api"]
  return MODEL["workhorse_fp"]


def screen_model_slots() -> List[Tuple[str, str]]:
  """
  Dual screen — Grok High (cursor) + gpt-5-mini (openai) by default.
  EW_LLM_SCREEN_DIVERSE=1 swaps slot A for base grok-4.5.
  EW_USE_GROK_HIGH=0 falls back to composer-2.5 slot A.
  """
  if os.environ.get("EW_LLM_SCREEN_DIVERSE", "").lower() in ("1", "true"):
    a = MODEL["screen_alt"]
  elif grok_high_enabled():
    a = grok_high_model()
  else:
    a = MODEL["workhorse_fp"]
  return [("cursor", a), ("openai", MODEL["screen_b"])]


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
  """
  Smart model pick for a task. Returns (model_id, tier_label, reason).
  Escalates only as far as disagreement + verdict require.
  """
  sev = disagreement_severity(stances or [])

  if task == "workhorse":
    m = workhorse_model()
    return m, "workhorse", "single cheap call — batch cap"

  if task == "screen":
    return "", "workhorse", "dual parallel — see screen_model_slots()"

  if task == "architect":
    return MODEL["fable"], "flagship", "multi-file deep reasoning"

  if task == "executive":
    return MODEL["opus"], "flagship", "GO + high conviction"

  if task == "synthesis":
    return MODEL["sol"], "crucial", "cross-pair executive summary"

  if task == "planning":
    if verdict == "CONDITIONAL_GO" and conviction != "high":
      return MODEL["light_plan"], "standard", "staged plan — luna saves tokens vs Sol"
    return MODEL["sol"], "crucial", "GO / staged planning"

  if task in ("tiebreaker", "review"):
    if sev == "mild":
      if grok_high_enabled():
        return grok_high_model(), "standard", "caution-only disagreement — Grok High not Sol/Opus"
      return MODEL["mild_tb"], "standard", "caution-only disagreement — Terra not Sol/Opus"
    if sev == "hard" and verdict == "GO" and conviction == "high":
      return MODEL["opus"], "flagship", "hard disagree on executive GO"
    if sev == "hard":
      return MODEL["sol"], "crucial", "hard disagreement"
    if grok_high_enabled():
      return grok_high_model(), "standard", "default mid review — Grok High"
    return MODEL["review"], "standard", "default mid review — Sonnet"

  return MODEL["sol"], "crucial", "fallback"


def roster_summary() -> Dict[str, Any]:
  """Full roster for --llm-tasks / docs."""
  assignments = []
  for task in (
    "workhorse",
    "screen",
    "tiebreaker_mild",
    "tiebreaker",
    "planning_light",
    "planning",
    "executive",
    "architect",
    "synthesis",
  ):
    if task == "screen":
      slots = screen_model_slots()
      model = " + ".join(m for _, m in slots)
      reason = "dual diverse families — parallel"
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
      "nano/composer for workhorse — never premium on batch",
      "dual screen: Grok High (cursor) + gpt-5-mini — diverse families",
      "mild disagree (caution vs agree) → Grok High (first-party), not Sol/Opus",
      "hard disagree → Sol; executive GO → Opus",
      "CONDITIONAL_GO planning → Luna; GO planning → Sol",
      "architect → Fable only; synthesis → Sol",
      "disk cache + critical-only gate + per-task output caps",
    ],
  }
