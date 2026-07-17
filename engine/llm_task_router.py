"""Task-aware model routing — cheap workhorses, premium for executive/architect/planning."""

from __future__ import annotations

import os
from typing import Any, Dict, List, Literal, Optional, Tuple

from engine.llm_backend import llm_backend
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
  "tiebreaker",  # ensemble phase 2 — disagreement, default premium
  "executive",   # GO + high conviction — premium decision
  "planning",    # CONDITIONAL_GO / staged — premium planning
  "architect",   # RepoMix, pipeline design — premium reasoning
  "synthesis",   # post-batch cross-pair summary — premium
]

Tier = Literal["cheap", "premium"]

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
  "tiebreaker": "premium",
  "executive": "premium",
  "planning": "premium",
  "architect": "premium",
  "synthesis": "premium",
}

# Cursor Pro model menu (first-party cheap, API premium)
CURSOR_MODELS: Dict[Tier, Dict[str, str]] = {
  "cheap": {
    "openai": os.environ.get("EW_CURSOR_CHEAP_OPENAI", "gpt-5-mini"),
    "anthropic": os.environ.get("EW_CURSOR_CHEAP_ANTHROPIC", "composer-2.5"),
    "workhorse": os.environ.get("EW_CURSOR_WORKHORSE", "composer-2.5"),
  },
  "premium": {
    "openai": os.environ.get("EW_CURSOR_PREMIUM_OPENAI", "gpt-5.2"),
    "anthropic": os.environ.get("EW_CURSOR_PREMIUM_ANTHROPIC", "claude-4.5-sonnet"),
    "executive": os.environ.get("EW_CURSOR_EXECUTIVE", "claude-4.5-sonnet"),
    "planning": os.environ.get("EW_CURSOR_PLANNING", "gpt-5.2"),
    "architect": os.environ.get("EW_CURSOR_ARCHITECT", "claude-4.5-sonnet"),
    "synthesis": os.environ.get("EW_CURSOR_SYNTHESIS", "gpt-5.2"),
  },
}

DIRECT_MODELS: Dict[Tier, Dict[str, str]] = {
  "cheap": {"openai": CHEAP_OPENAI, "anthropic": CHEAP_ANTHROPIC},
  "premium": {"openai": STANDARD_OPENAI, "anthropic": STANDARD_ANTHROPIC},
}

TASK_DESCRIPTIONS: Dict[TaskKind, str] = {
  "workhorse": "High-volume cheap screen (batch --llm-advisory-max)",
  "screen": "Dual cheap parallel review before escalation",
  "tiebreaker": "Premium call when cheap models disagree",
  "executive": "GO + high conviction final risk decision",
  "planning": "CONDITIONAL_GO / staged entry planning",
  "architect": "RepoMix / multi-file pipeline design",
  "synthesis": "Post-batch executive summary across top setups",
}


def max_output_for_task(task: TaskKind) -> int:
  return TASK_OUTPUT_TOKENS.get(task, DEFAULT_MAX_OUTPUT_TOKENS)


def tier_for_task(task: TaskKind) -> Tier:
  return TASK_TIER.get(task, "cheap")


def tiebreaker_task(verdict: str, conviction: str = "") -> TaskKind:
  """Pick premium task class for escalation — executive > planning > tiebreaker."""
  if verdict == "GO" and conviction == "high":
    return "executive"
  if verdict in ("GO", "CONDITIONAL_GO", "STAGED_GO"):
    return "planning"
  return "tiebreaker"


def screen_task_for_mode(mode: str) -> TaskKind:
  return "workhorse" if mode == "single" else "screen"


def resolve_model(provider: Provider, task: TaskKind) -> Tuple[str, Tier, int]:
  """
  Resolve (model_id, tier, max_output_tokens) for a task.
  Cheap tasks always use workhorse/screen tier — never premium unless task says so.
  """
  tier = tier_for_task(task)
  max_out = max_output_for_task(task)

  if llm_backend() == "cursor":
    menu = CURSOR_MODELS[tier]
    if task == "workhorse":
      model = menu.get("workhorse") or menu.get("anthropic") or menu["openai"]
    elif task == "executive":
      model = menu.get("executive") or menu["anthropic"]
    elif task == "planning":
      model = menu.get("planning") or menu["openai"]
    elif task == "architect":
      model = menu.get("architect") or menu["anthropic"]
    elif task == "synthesis":
      model = menu.get("synthesis") or menu["openai"]
    else:
      model = menu.get(provider) or menu["openai"]
    return model, tier, max_out

  return model_for(provider, tier), tier, max_out


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
  for provider in ("openai", "anthropic"):
    if llm_backend() == "direct":
      key = "OPENAI_API_KEY" if provider == "openai" else "ANTHROPIC_API_KEY"
      if not os.environ.get(key, "").strip():
        continue
    model, tier, max_out = resolve_model(provider, task)
    routes.append((provider, model, tier, task, max_out))
  return routes


def tiebreaker_route(verdict: str, conviction: str = "") -> Optional[Tuple[Provider, str, Tier, TaskKind, int]]:
  task = tiebreaker_task(verdict, conviction)
  provider: Provider = "openai"
  if llm_backend() == "direct":
    if os.environ.get("OPENAI_API_KEY", "").strip():
      provider = "openai"
    elif os.environ.get("ANTHROPIC_API_KEY", "").strip():
      provider = "anthropic"
    else:
      return None
  model, tier, max_out = resolve_model(provider, task)
  return provider, model, tier, task, max_out


def routing_matrix() -> Dict[str, Any]:
  """Human-readable task → model → token matrix for --llm-tasks."""
  rows = []
  for task in TASK_DESCRIPTIONS:
    tier = tier_for_task(task)
    max_out = max_output_for_task(task)
    if llm_backend() == "cursor":
      m_o, _, _ = resolve_model("openai", task)  # type: ignore[arg-type]
      m_a, _, _ = resolve_model("anthropic", task)  # type: ignore[arg-type]
      models = f"{m_a} + {m_o}" if task == "screen" else (m_a if task in ("executive", "architect") else m_o)
    else:
      models = f"{DIRECT_MODELS[tier]['anthropic']} / {DIRECT_MODELS[tier]['openai']}"
    rows.append(
      {
        "task": task,
        "tier": tier,
        "max_output_tokens": max_out,
        "models": models,
        "when": TASK_DESCRIPTIONS[task],
        "pool": "first-party" if tier == "cheap" and llm_backend() == "cursor" else ("api" if tier == "premium" else "cheap"),
      }
    )
  return {
    "backend": llm_backend(),
    "principle": "Cheap workhorses for volume; premium only for executive, planning, architect, synthesis.",
    "tasks": rows,
    "token_savers": [
      "Critical-only gate (~90% batch pairs skip LLM)",
      "Compact JSON prompts (~450 input tokens)",
      "Per-task output caps (workhorse 180, screen 200)",
      "Disk cache 1h (zero tokens on repeat)",
      "Premium tiebreaker only on disagreement (~30%)",
      "Batch cap --llm-advisory-max 5",
    ],
  }
