"""Task-aware model routing — roster-driven, cheap workhorses, premium only when crucial."""

from __future__ import annotations

import os
from typing import Any, Dict, List, Literal, Optional, Tuple

from engine.llm_backend import llm_backend
from engine.llm_model_roster import (
  MODEL,
  ROSTER,
  disagreement_severity,
  escalate_task_model,
  roster_summary,
  screen_model_slots,
  workhorse_model,
)
from engine.llm_token_router import (
  CHEAP_ANTHROPIC,
  CHEAP_OPENAI,
  DEFAULT_MAX_OUTPUT_TOKENS,
  STANDARD_ANTHROPIC,
  STANDARD_OPENAI,
  Provider,
  model_for,
)

TaskKind = Literal[
  "workhorse",   # single cheap call — batch caps, high volume
  "screen",      # ensemble phase 1 — dual cheap parallel
  "tiebreaker",  # ensemble phase 2 — disagreement escalation
  "executive",   # GO + high conviction — premium decision
  "planning",    # CONDITIONAL_GO / staged — premium planning
  "architect",   # RepoMix, pipeline design — premium reasoning
  "synthesis",   # post-batch cross-pair summary — premium
]

Tier = Literal["cheap", "standard", "premium"]

# Token caps per task — workhorse/screen stay minimal
TASK_OUTPUT_TOKENS: Dict[TaskKind, int] = {
  "workhorse": int(os.environ.get("EW_LLM_MAX_OUTPUT_WORKHORSE", "180")),
  "screen": int(os.environ.get("EW_LLM_MAX_OUTPUT_SCREEN", "200")),
  "tiebreaker": int(os.environ.get("EW_LLM_MAX_OUTPUT_TIEBREAKER", "240")),
  "executive": int(os.environ.get("EW_LLM_MAX_OUTPUT_EXECUTIVE", "280")),
  "planning": int(os.environ.get("EW_LLM_MAX_OUTPUT_PLANNING", "320")),
  "architect": int(os.environ.get("EW_LLM_MAX_OUTPUT_ARCHITECT", "600")),
  "synthesis": int(os.environ.get("EW_LLM_MAX_OUTPUT_SYNTHESIS", "500")),
}

TASK_TIER: Dict[TaskKind, Tier] = {
  "workhorse": "cheap",
  "screen": "cheap",
  "tiebreaker": "standard",
  "executive": "premium",
  "planning": "premium",
  "architect": "premium",
  "synthesis": "premium",
}

# Backward-compat exports (roster-resolved)
CURSOR_OPUS = MODEL["opus"]
CURSOR_FABLE = MODEL["fable"]
CURSOR_SOL = MODEL["sol"]

# Direct API crucial fallbacks when not on Cursor
DIRECT_CRUCIAL: Dict[TaskKind, str] = {
  "tiebreaker": os.environ.get("EW_DIRECT_SOL", STANDARD_OPENAI),
  "executive": os.environ.get("EW_DIRECT_OPUS", STANDARD_ANTHROPIC),
  "planning": os.environ.get("EW_DIRECT_SOL", STANDARD_OPENAI),
  "architect": os.environ.get("EW_DIRECT_FABLE", STANDARD_ANTHROPIC),
  "synthesis": os.environ.get("EW_DIRECT_SOL", STANDARD_OPENAI),
}

DIRECT_MODELS: Dict[str, Dict[str, str]] = {
  "cheap": {"openai": CHEAP_OPENAI, "anthropic": CHEAP_ANTHROPIC},
  "standard": {"openai": STANDARD_OPENAI, "anthropic": STANDARD_ANTHROPIC},
  "premium": {"openai": STANDARD_OPENAI, "anthropic": STANDARD_ANTHROPIC},
}

TASK_DESCRIPTIONS: Dict[TaskKind, str] = {
  "workhorse": "High-volume cheap screen (batch --llm-advisory-max)",
  "screen": "Dual cheap parallel review before escalation",
  "tiebreaker": "Terra (mild) or Sol/Opus (hard) when cheap models disagree",
  "executive": "Claude Opus — GO + high conviction + hard disagreement",
  "planning": "Luna (light) or Sol (full) — CONDITIONAL_GO / staged entry",
  "architect": "Claude Fable — RepoMix / multi-file pipeline design",
  "synthesis": "GPT-5.6 Sol — post-batch executive summary across top setups",
}

_ROSTER_TIER_MAP: Dict[str, Tier] = {
  "nano": "cheap",
  "workhorse": "cheap",
  "standard": "standard",
  "crucial": "premium",
  "flagship": "premium",
}


def _roster_tier_to_task_tier(roster_tier: str, task: TaskKind) -> Tier:
  mapped = _ROSTER_TIER_MAP.get(roster_tier, TASK_TIER.get(task, "cheap"))
  return mapped  # type: ignore[return-value]


def _provider_for_model(model_id: str) -> Provider:
  meta = ROSTER.get(model_id, {})
  family = meta.get("family", "openai")
  if family == "anthropic":
    return "anthropic"
  return "openai"


def crucial_model_for_task(
  task: TaskKind,
  verdict: str = "GO",
  conviction: str = "high",
  stances: Optional[List[str]] = None,
) -> str:
  """Model id for a task — roster escalation when stances provided."""
  if llm_backend() == "cursor":
    model, _, _ = escalate_task_model(task, verdict, conviction, stances)
    return model
  return DIRECT_CRUCIAL.get(task, model_for("openai", "standard"))


def provider_for_task(task: TaskKind, model_id: str = "") -> Provider:
  """Anthropic slot for Opus/Fable; OpenAI slot for Sol/Luna/Terra."""
  if model_id:
    return _provider_for_model(model_id)
  if task in ("executive", "architect"):
    return "anthropic"
  return "openai"


def max_output_for_task(task: TaskKind) -> int:
  return TASK_OUTPUT_TOKENS.get(task, DEFAULT_MAX_OUTPUT_TOKENS)


def tier_for_task(task: TaskKind) -> Tier:
  return TASK_TIER.get(task, "cheap")


def tiebreaker_task(
  verdict: str,
  conviction: str = "",
  stances: Optional[List[str]] = None,
) -> TaskKind:
  """
  Pick task class for escalation.
  Mild disagreement always stays tiebreaker (Terra) — never burns Opus/Sol.
  """
  sev = disagreement_severity(stances or [])
  if sev == "mild":
    return "tiebreaker"
  if verdict == "GO" and conviction == "high":
    return "executive"
  if verdict in ("GO", "CONDITIONAL_GO", "STAGED_GO"):
    return "planning"
  return "tiebreaker"


def screen_task_for_mode(mode: str) -> TaskKind:
  return "workhorse" if mode == "single" else "screen"


def resolve_model(
  provider: Provider,
  task: TaskKind,
  verdict: str = "",
  conviction: str = "",
  stances: Optional[List[str]] = None,
) -> Tuple[str, Tier, int]:
  """
  Resolve (model_id, tier, max_output_tokens) for a task.
  Cheap: workhorse/screen. Standard/premium: roster escalation.
  """
  max_out = max_output_for_task(task)

  if task in ("workhorse", "screen"):
    if llm_backend() == "cursor":
      if task == "workhorse":
        return workhorse_model(), "cheap", max_out
      for slot_provider, model in screen_model_slots():
        if slot_provider == provider or provider in ("openai", "anthropic"):
          if task == "screen":
            if (provider == "anthropic" and slot_provider == "anthropic") or (
              provider == "openai" and slot_provider == "openai"
            ):
              return model, "cheap", max_out
      slots = screen_model_slots()
      if provider == "anthropic" and slots:
        return slots[0][1], "cheap", max_out
      if provider == "openai" and len(slots) > 1:
        return slots[1][1], "cheap", max_out
      return workhorse_model(), "cheap", max_out
    return model_for(provider, "cheap"), "cheap", max_out

  if llm_backend() == "cursor":
    model, roster_tier, _ = escalate_task_model(task, verdict, conviction, stances)
    tier = _roster_tier_to_task_tier(roster_tier, task)
    return model, tier, max_out

  tier = tier_for_task(task)
  return DIRECT_CRUCIAL.get(task, model_for(provider, "standard")), tier, max_out


def screen_routes(mode: str) -> List[Tuple[Provider, str, Tier, TaskKind, int]]:
  """Routes for advisory screen phase — always cheap tier."""
  task = screen_task_for_mode(mode)
  if mode == "single":
    provider: Provider = "openai"
    if llm_backend() == "direct":
      if os.environ.get("OPENAI_API_KEY", "").strip():
        provider = "openai"
      elif os.environ.get("ANTHROPIC_API_KEY", "").strip():
        provider = "anthropic"
      else:
        return []
    model, tier, max_out = resolve_model(provider, task)
    return [(provider, model, tier, task, max_out)]

  routes: List[Tuple[Provider, str, Tier, TaskKind, int]] = []
  if llm_backend() == "cursor":
    for slot_label, model in screen_model_slots():
      provider = slot_label if slot_label in ("openai", "anthropic") else "anthropic"
      if slot_label == "openai":
        provider = "openai"
      tier: Tier = "cheap"
      max_out = max_output_for_task(task)
      routes.append((provider, model, tier, task, max_out))
    return routes

  for provider in ("openai", "anthropic"):
    if llm_backend() == "direct":
      key = "OPENAI_API_KEY" if provider == "openai" else "ANTHROPIC_API_KEY"
      if not os.environ.get(key, "").strip():
        continue
    model, tier, max_out = resolve_model(provider, task)
    routes.append((provider, model, tier, task, max_out))
  return routes


def tiebreaker_route(
  verdict: str,
  conviction: str = "",
  stances: Optional[List[str]] = None,
) -> Optional[Tuple[Provider, str, Tier, TaskKind, int]]:
  task = tiebreaker_task(verdict, conviction, stances)
  if llm_backend() == "cursor":
    model, roster_tier, _ = escalate_task_model(task, verdict, conviction, stances)
    tier = _roster_tier_to_task_tier(roster_tier, task)
    provider = provider_for_task(task, model)
    max_out = max_output_for_task(task)
    return provider, model, tier, task, max_out

  provider = provider_for_task(task)
  if llm_backend() == "direct":
    key = "OPENAI_API_KEY" if provider == "openai" else "ANTHROPIC_API_KEY"
    if not os.environ.get(key, "").strip():
      alt: Provider = "anthropic" if provider == "openai" else "openai"
      if os.environ.get("OPENAI_API_KEY" if alt == "openai" else "ANTHROPIC_API_KEY", "").strip():
        provider = alt
      else:
        return None
  model, tier, max_out = resolve_model(provider, task, verdict, conviction, stances)
  return provider, model, tier, task, max_out


def routing_matrix() -> Dict[str, Any]:
  """Human-readable task → model → token matrix for --llm-tasks."""
  roster = roster_summary()
  rows = []
  for task in TASK_DESCRIPTIONS:
    tier = tier_for_task(task)
    max_out = max_output_for_task(task)
    if llm_backend() == "cursor":
      if task == "screen":
        models = " + ".join(m for _, m in screen_model_slots())
      elif task == "workhorse":
        models = workhorse_model()
      elif task == "tiebreaker":
        mild_m, _, _ = escalate_task_model("tiebreaker", stances=["agree", "caution"])
        hard_m, _, _ = escalate_task_model("tiebreaker", "GO", "high", ["agree", "reject"])
        models = f"{mild_m} (mild) / {hard_m} (hard)"
      elif task == "planning":
        light_m, _, _ = escalate_task_model("planning", "CONDITIONAL_GO", "medium")
        full_m, _, _ = escalate_task_model("planning", "GO", "high")
        models = f"{light_m} (light) / {full_m} (full)"
      else:
        models = crucial_model_for_task(task)
    else:
      models = f"{DIRECT_MODELS['cheap']['anthropic']} / {DIRECT_MODELS['cheap']['openai']}"
    rows.append(
      {
        "task": task,
        "tier": tier,
        "max_output_tokens": max_out,
        "models": models,
        "when": TASK_DESCRIPTIONS[task],
        "pool": "first-party" if tier == "cheap" and llm_backend() == "cursor" else ("api" if tier == "premium" else "mixed"),
      }
    )
  return {
    "backend": llm_backend(),
    "principle": (
      "Every model in the roster — cheap nano/composer for volume, "
      "Terra/Luna for mid escalation, Opus/Fable/Sol only when crucial."
    ),
    "crucial_models": {
      "opus": CURSOR_OPUS,
      "fable": CURSOR_FABLE,
      "sol": CURSOR_SOL,
      "terra": MODEL["mild_tb"],
      "luna": MODEL["light_plan"],
    },
    "tasks": rows,
    "roster": roster,
    "token_savers": roster["efficiency_rules"],
  }
