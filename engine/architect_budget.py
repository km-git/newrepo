"""GPT-5.6 decision/advise/architect routing with 10K token ceiling and cache."""

from __future__ import annotations

import hashlib
import json
import os
from typing import Any, Dict, List, Literal, Optional, Tuple

from cachetools import TTLCache

from cache.disk_cache import CompressedCache, get_cache
from engine.llm_gpt_policy import per_model_token_limit
from engine.llm_model_roster import MODEL, escalate_task_model
from engine.llm_token_saver import estimate_tokens as count_tokens

DecisionTask = Literal["advise", "decision", "architect", "planning", "tiebreaker", "executive"]

GPT56_DECISION_MODEL = os.environ.get("EW_MODEL_SOL", MODEL["sol"])
ARCHITECT_TOKEN_CEILING = per_model_token_limit()
ARCHITECT_CACHE_NS = "architect_decision_v1"
ARCHITECT_CACHE_TTL = int(os.environ.get("EW_ARCHITECT_CACHE_TTL", "86400"))

# Hot in-memory LRU (cachetools) — avoids disk read on repeat calls in same session
_memory_cache: TTLCache = TTLCache(maxsize=128, ttl=3600)

# Compact system prompts — no prose
SYSTEM_PROMPTS: Dict[DecisionTask, str] = {
  "advise": "Advisor. JSON: recommendation, risks[], confidence, next_step.",
  "decision": "Decide. JSON: choice, rationale, blockers[], proceed(bool).",
  "architect": "Architect. JSON: isc, schema{}, files[], deps[].",
  "planning": "Plan. JSON: phases[], milestones[], risks[].",
  "tiebreaker": "Tiebreak. JSON: winner, reason, confidence.",
  "executive": "Executive. JSON: verdict, conviction, action.",
}


def compact_json(data: Any) -> str:
  return json.dumps(data, separators=(",", ":"), default=str)


def trim_context(text: str, max_tokens: int, model: str = GPT56_DECISION_MODEL) -> Tuple[str, bool]:
  """Trim text to fit token budget. Returns (trimmed, was_trimmed)."""
  if count_tokens(text) <= max_tokens:
    return text, False
  # Binary search by char slice
  lo, hi = 0, len(text)
  while lo < hi:
    mid = (lo + hi + 1) // 2
    if count_tokens(text[:mid]) <= max_tokens:
      lo = mid
    else:
      hi = mid - 1
  return text[:lo] + "\n...[trimmed]", True


def build_compact_prompt(
  task: DecisionTask,
  payload: dict,
  extra_context: str = "",
  max_input_tokens: Optional[int] = None,
) -> Tuple[str, dict]:
  """
  Build minimal prompt for GPT-5.6 decision calls.
  Returns (prompt, budget_report).
  """
  ceiling = max_input_tokens or (ARCHITECT_TOKEN_CEILING - _default_max_output(task))
  sys_p = SYSTEM_PROMPTS.get(task, SYSTEM_PROMPTS["decision"])
  blob = compact_json(payload)
  ctx = f"\nCTX:{extra_context}" if extra_context else ""
  prompt = f"{sys_p}\n\nDATA:{blob}{ctx}\n\nJSON:"

  trimmed = False
  if count_tokens(prompt) > ceiling:
    # Shrink payload first, then context
    for key in list(payload.keys()):
      if isinstance(payload[key], (list, dict, str)) and len(str(payload[key])) > 200:
        payload[key] = str(payload[key])[:200]
    blob = compact_json(payload)
    prompt = f"{sys_p}\n\nDATA:{blob}{ctx}\n\nJSON:"
    if count_tokens(prompt) > ceiling and extra_context:
      extra_context, trimmed = trim_context(extra_context, max(500, ceiling // 4))
      ctx = f"\nCTX:{extra_context}"
      prompt = f"{sys_p}\n\nDATA:{blob}{ctx}\n\nJSON:"
    if count_tokens(prompt) > ceiling:
      prompt, trimmed = trim_context(prompt, ceiling)

  max_out = _default_max_output(task)
  report = token_budget_report(prompt, max_out, task)
  report["trimmed"] = trimmed
  return prompt, report


def _default_max_output(task: DecisionTask) -> int:
  from engine.llm_task_router import max_output_for_task

  mapping = {
    "advise": "tiebreaker",
    "decision": "tiebreaker",
    "architect": "architect",
    "planning": "planning",
    "tiebreaker": "tiebreaker",
    "executive": "executive",
  }
  return max_output_for_task(mapping.get(task, "tiebreaker"))  # type: ignore[arg-type]


def token_budget_report(prompt: str, max_output: int, task: DecisionTask) -> dict:
  est_in = count_tokens(prompt)
  est_total = est_in + max_output
  return {
    "task": task,
    "model": GPT56_DECISION_MODEL,
    "est_input_tokens": est_in,
    "max_output_tokens": max_output,
    "est_total_tokens": est_total,
    "ceiling": ARCHITECT_TOKEN_CEILING,
    "within_budget": est_total <= ARCHITECT_TOKEN_CEILING,
    "headroom": ARCHITECT_TOKEN_CEILING - est_total,
  }


def cache_key(task: DecisionTask, prompt: str) -> str:
  digest = hashlib.sha256(f"{task}:{prompt}".encode()).hexdigest()[:24]
  return digest


def get_cached_decision(
  task: DecisionTask,
  prompt: str,
  cache: Optional[CompressedCache] = None,
) -> Optional[dict]:
  key = (task, cache_key(task, prompt))
  if key in _memory_cache:
    return _memory_cache[key]
  c = cache or get_cache()
  hit = c.get(ARCHITECT_CACHE_NS, task, cache_key(task, prompt))
  if hit is not None:
    _memory_cache[key] = hit
  return hit


def cache_decision(
  task: DecisionTask,
  prompt: str,
  result: dict,
  cache: Optional[CompressedCache] = None,
) -> str:
  key = (task, cache_key(task, prompt))
  _memory_cache[key] = result
  c = cache or get_cache()
  return c.set(ARCHITECT_CACHE_NS, result, task, cache_key(task, prompt))


def route_gpt56_decision(
  task: DecisionTask,
  verdict: str = "",
  conviction: str = "",
  stances: Optional[List[str]] = None,
) -> Tuple[str, str, bool]:
  """
  Route to GPT-5.6 Sol for decision/advise/architect tasks (under 10K token ceiling).
  Returns (model_id, reason, use_gpt56).
  """
  gpt56_tasks = frozenset({"advise", "decision", "architect", "planning", "synthesis"})
  if task not in gpt56_tasks:
    return workhorse_fallback(), "implementation task — use Haiku/workhorse", False

  if task == "architect":
    return GPT56_DECISION_MODEL, f"architect plan — GPT-5.6 Sol (<{ARCHITECT_TOKEN_CEILING} tok)", True
  if task in ("advise", "decision"):
    return GPT56_DECISION_MODEL, f"{task} — GPT-5.6 Sol (<{ARCHITECT_TOKEN_CEILING} tok)", True
  if task == "planning":
    model, _, reason = escalate_task_model("planning", verdict, conviction, stances)
    if "gpt-5.6" in model:
      return model, f"{reason} (<{ARCHITECT_TOKEN_CEILING} tok)", True
    return model, reason, False
  return GPT56_DECISION_MODEL, "synthesis — GPT-5.6 Sol", True


def workhorse_fallback() -> str:
  from engine.llm_model_roster import workhorse_model

  return workhorse_model()


def enforce_budget_or_raise(report: dict) -> dict:
  if not report.get("within_budget"):
    raise TokenBudgetExceeded(
      f"Estimated {report['est_total_tokens']} tokens exceeds ceiling {ARCHITECT_TOKEN_CEILING}"
    )
  return report


class TokenBudgetExceeded(ValueError):
  pass


def prepare_decision_call(
  task: DecisionTask,
  payload: dict,
  extra_context: str = "",
  use_cache: bool = True,
  cache: Optional[CompressedCache] = None,
) -> dict:
  """
  Full pipeline: build prompt → check budget → cache lookup.
  Returns call package for LLM invocation.
  """
  prompt, budget = build_compact_prompt(task, payload, extra_context)
  enforce_budget_or_raise(budget)

  if use_cache:
    hit = get_cached_decision(task, prompt, cache)
    if hit is not None:
      return {
        "prompt": prompt,
        "budget": {**budget, "cache_hit": True},
        "cached_result": hit,
        "model": GPT56_DECISION_MODEL,
        "skip_llm": True,
      }

  model, reason, use_gpt = route_gpt56_decision(task)
  return {
    "prompt": prompt,
    "budget": {**budget, "cache_hit": False},
    "model": model if use_gpt else workhorse_fallback(),
    "route_reason": reason,
    "skip_llm": False,
    "token_savers": token_saver_checklist(),
  }


def token_saver_checklist() -> List[str]:
  base = [
    "compact JSON (no indent)",
    "short system prompt",
    "diskcache architect decisions (24h TTL)",
    "llm_token_saver tiktoken counting",
    f"{ARCHITECT_TOKEN_CEILING} token ceiling per model (llm_gpt_policy)",
    "trim context before send",
    "cachetools LRU for hot keys",
    "token_saver_registry (llm-token-optimizer, tokenpruner, cachetic)",
    "Cmd+K workhorse for implementation (not GPT)",
  ]
  return base


def store_decision_result(
  task: DecisionTask,
  prompt: str,
  result: dict,
  cache: Optional[CompressedCache] = None,
) -> str:
  return cache_decision(task, prompt, result, cache)
