"""LLM cost estimation — cheap-by-default routing with premium only where it earns its keep."""

from __future__ import annotations

from typing import Any, Dict, List, Literal, Optional, Tuple

from engine.llm_token_router import (
  CHEAP_ANTHROPIC,
  CHEAP_OPENAI,
  DEFAULT_MAX_OUTPUT_TOKENS,
  STANDARD_ANTHROPIC,
  STANDARD_OPENAI,
  Provider,
  model_for,
)

# USD per 1M tokens (Jul 2026 list prices — override via env if needed)
MODEL_PRICING: Dict[str, Dict[str, float]] = {
  CHEAP_OPENAI: {"input": 0.15, "output": 0.60},
  STANDARD_OPENAI: {"input": 2.50, "output": 10.00},
  CHEAP_ANTHROPIC: {"input": 0.80, "output": 4.00},
  STANDARD_ANTHROPIC: {"input": 3.00, "output": 15.00},
}

TaskKind = Literal["screen", "tiebreaker", "architect", "synthesis"]

# Which model tier each task class uses — cheap unless complexity demands premium
TASK_TIER: Dict[TaskKind, str] = {
  "screen": "cheap",        # risk JSON review, batch advisory gate
  "tiebreaker": "standard", # disagreeing cheap models → one premium call
  "architect": "standard",  # RepoMix review, pipeline design, multi-TF synthesis
  "synthesis": "standard",  # post-batch executive summary across top setups
}

# Typical compact advisory prompt size (measured ~400–500 tokens)
TYPICAL_ADVISORY_INPUT_TOKENS = 450
TYPICAL_ADVISORY_OUTPUT_TOKENS = 180


def task_tier(task: TaskKind) -> str:
  return TASK_TIER.get(task, "cheap")


def model_for_task(provider: Provider, task: TaskKind) -> str:
  return model_for(provider, task_tier(task))


def estimate_call_cost(model: str, input_tokens: int, output_tokens: int) -> float:
  rates = MODEL_PRICING.get(model)
  if not rates:
    return 0.0
  return round(
    (input_tokens * rates["input"] + output_tokens * rates["output"]) / 1_000_000,
    6,
  )


def estimate_routes_cost(
  routes: List[Tuple[Provider, str, str]],
  input_tokens: int,
  output_tokens: int = TYPICAL_ADVISORY_OUTPUT_TOKENS,
) -> Dict[str, Any]:
  """Sum cost for a list of (provider, model, tier) routes."""
  per_route = []
  total = 0.0
  for provider, model, tier in routes:
    cost = estimate_call_cost(model, input_tokens, output_tokens)
    per_route.append(
      {
        "provider": provider,
        "model": model,
        "tier": tier,
        "input_tokens": input_tokens,
        "output_tokens": output_tokens,
        "est_cost_usd": cost,
      }
    )
    total += cost
  return {
    "routes": per_route,
    "est_total_usd": round(total, 6),
    "input_tokens": input_tokens,
    "output_tokens_per_call": output_tokens,
  }


def advisory_scenario_comparison(
  input_tokens: int = TYPICAL_ADVISORY_INPUT_TOKENS,
  output_tokens: int = TYPICAL_ADVISORY_OUTPUT_TOKENS,
  tiebreaker_rate: float = 0.30,
) -> Dict[str, Any]:
  """
  Cost comparison for a typical critical advisory (~450 in / ~180 out per call).

  Scenarios reflect how the tool actually routes — cheap first, premium only on disagreement.
  """
  cheap_o = CHEAP_OPENAI
  cheap_a = CHEAP_ANTHROPIC
  prem_o = STANDARD_OPENAI
  prem_a = STANDARD_ANTHROPIC

  def _one(model: str) -> float:
    return estimate_call_cost(model, input_tokens, output_tokens)

  single_cheap = _one(cheap_o)
  dual_cheap = _one(cheap_o) + _one(cheap_a)
  ensemble_agree = dual_cheap
  ensemble_disagree = dual_cheap + _one(prem_o)
  ensemble_blended = round(
    ensemble_agree * (1 - tiebreaker_rate) + ensemble_disagree * tiebreaker_rate, 6
  )
  dual_premium = _one(prem_o) + _one(prem_a)
  single_premium = _one(prem_o)

  scenarios = [
    {
      "id": "single_cheap",
      "label": "Single cheap (EW_LLM_INTELLIGENCE=single)",
      "models": [cheap_o],
      "calls": 1,
      "est_cost_usd": single_cheap,
      "recommended": "batch / high-volume",
    },
    {
      "id": "ensemble_agree",
      "label": "Ensemble — models agree (no tiebreaker)",
      "models": [cheap_o, cheap_a],
      "calls": 2,
      "est_cost_usd": ensemble_agree,
      "recommended": "default — best quality/cost when unanimous",
    },
    {
      "id": "ensemble_disagree",
      "label": "Ensemble — disagree (+ premium tiebreaker)",
      "models": [cheap_o, cheap_a, prem_o],
      "calls": 3,
      "est_cost_usd": ensemble_disagree,
      "recommended": "hard decisions only",
    },
    {
      "id": "ensemble_blended",
      "label": f"Ensemble blended (~{int(tiebreaker_rate * 100)}% tiebreaker rate)",
      "models": [cheap_o, cheap_a, f"{prem_o} (conditional)"],
      "calls": f"2–3 (avg {2 + tiebreaker_rate:.1f})",
      "est_cost_usd": ensemble_blended,
      "recommended": "expected real-world cost",
    },
    {
      "id": "dual_premium",
      "label": "Dual premium (NOT recommended)",
      "models": [prem_o, prem_a],
      "calls": 2,
      "est_cost_usd": dual_premium,
      "recommended": "avoid — use ensemble instead",
    },
    {
      "id": "cache_hit",
      "label": "Disk cache hit (same symbol/verdict/price)",
      "models": [],
      "calls": 0,
      "est_cost_usd": 0.0,
      "recommended": "free",
    },
  ]

  savings_vs_dual_premium = round(
    (1 - ensemble_blended / dual_premium) * 100 if dual_premium else 0, 1
  )
  savings_vs_single_premium = round(
    (1 - ensemble_blended / single_premium) * 100 if single_premium else 0, 1
  )

  return {
    "typical_input_tokens": input_tokens,
    "typical_output_tokens": output_tokens,
    "tiebreaker_assumption_pct": int(tiebreaker_rate * 100),
    "task_tiers": dict(TASK_TIER),
    "scenarios": scenarios,
    "savings_pct_vs_dual_premium": savings_vs_dual_premium,
    "savings_pct_vs_single_premium": savings_vs_single_premium,
    "guidance": (
      "Use cheap models for screen/advisory; escalate to premium only for tiebreakers, "
      "architect review (RepoMix), and post-batch synthesis."
    ),
  }


def attach_cost_estimate(
  budget: dict,
  routes: List[Tuple[Provider, str, str]],
  *,
  escalated: bool = False,
  tiebreaker_route: Optional[Tuple[Provider, str, str]] = None,
  actual_usage: Optional[dict] = None,
) -> dict:
  """Merge USD cost estimate into token_budget report."""
  input_tokens = budget.get("est_input_tokens", TYPICAL_ADVISORY_INPUT_TOKENS)
  output_tokens = budget.get("max_output_tokens", DEFAULT_MAX_OUTPUT_TOKENS)

  all_routes = list(routes)
  if escalated and tiebreaker_route:
    all_routes.append(tiebreaker_route)

  cost = estimate_routes_cost(all_routes, input_tokens, min(output_tokens, TYPICAL_ADVISORY_OUTPUT_TOKENS + 100))
  budget = dict(budget)
  budget["cost_estimate"] = cost

  if actual_usage:
    budget["cost_actual"] = actual_usage

  budget["scenario_comparison"] = advisory_scenario_comparison(
    input_tokens=input_tokens,
    output_tokens=min(output_tokens, TYPICAL_ADVISORY_OUTPUT_TOKENS + 100),
  )
  return budget
