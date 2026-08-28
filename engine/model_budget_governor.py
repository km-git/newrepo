"""
Model budget governor — 90% cheap Cursor models, premium only when smartly required.

Tracks cheap vs premium call ratio per day and gates escalation for:
  - executive decision-making (GO + high conviction, hard disagreement)
  - self-improvement (poor metrics, hard disagreement)
Routine tasks (TV OSS, social, research screens) stay on cheapest workhorse models.
"""

from __future__ import annotations

import os
from datetime import date
from typing import Any, Dict, List, Literal, Optional, Tuple

from engine.llm_model_roster import MODEL, ROSTER, disagreement_severity, workhorse_model

Purpose = Literal["routine", "screen", "self_improvement", "executive", "research"]

CHEAP_TIERS = frozenset({"nano", "workhorse", "cheap"})
PREMIUM_TIERS = frozenset({"standard", "crucial", "flagship", "premium"})


def cheap_target_ratio() -> float:
  """Target fraction of LLM calls on cheap models (default 90%)."""
  return float(os.environ.get("EW_CHEAP_MODEL_RATIO", "0.90"))


def premium_escalation_mode() -> str:
  """smart (default) | always | never"""
  return os.environ.get("EW_PREMIUM_ESCALATION", "smart").lower().strip()


def governor_enabled() -> bool:
  return os.environ.get("EW_MODEL_BUDGET_GOVERNOR", "1").lower() not in ("0", "false", "no")


def routine_llm_enabled() -> bool:
  """Routine consensus (TV OSS, social) — off by default to save tokens."""
  return os.environ.get("EW_ROUTINE_LLM", "0").lower() in ("1", "true", "yes")


def _tier_is_cheap(tier: str) -> bool:
  return (tier or "cheap").lower() in CHEAP_TIERS


def _roster_tier(model_id: str) -> str:
  return str((ROSTER.get(model_id) or {}).get("tier", "workhorse"))


class ModelBudgetGovernor:
  """Daily cheap/premium call tracker with 90/10 enforcement."""

  _daily: Dict[str, Dict[str, int]] = {}

  def __init__(self) -> None:
    self._day = date.today().isoformat()

  def _state(self) -> dict:
    return dict(self._daily.get(self._day, {"cheap": 0, "premium": 0}))

  def _save(self, state: dict) -> None:
    self._daily[self._day] = state

  def record_call(self, tier: str, model: str = "") -> None:
    state = self._state()
    roster_tier = _roster_tier(model) if model else tier
    bucket = "cheap" if _tier_is_cheap(tier) or roster_tier in ("nano", "workhorse") else "premium"
    state[bucket] = int(state.get(bucket, 0)) + 1
    self._save(state)

  def cheap_ratio(self) -> float:
    state = self._state()
    cheap = int(state.get("cheap", 0))
    premium = int(state.get("premium", 0))
    total = cheap + premium
    if total == 0:
      return 1.0
    return cheap / total

  def premium_share(self) -> float:
    return 1.0 - self.cheap_ratio()

  def premium_budget_allows(self) -> bool:
    """True when premium share is below (1 - cheap_target_ratio)."""
    if not governor_enabled():
      return True
    if premium_escalation_mode() == "never":
      return False
    if premium_escalation_mode() == "always":
      return True
    max_premium = 1.0 - cheap_target_ratio()
    return self.premium_share() < max_premium + 0.001

  def should_escalate_to_premium(
    self,
    purpose: Purpose,
    *,
    verdict: str = "",
    conviction: str = "",
    stances: Optional[List[str]] = None,
    metrics_poor: bool = False,
    force_critical: bool = False,
  ) -> bool:
    """
    Gate premium model usage — only executive + self-improvement when warranted.
    """
    if premium_escalation_mode() == "never":
      return False
    if purpose in ("routine", "screen", "research"):
      return False

    sev = disagreement_severity(stances or [])

    if purpose == "executive":
      if verdict not in ("GO", "CONDITIONAL_GO"):
        return False
      if force_critical or (verdict == "GO" and conviction in ("high", "medium") and sev == "hard"):
        return self.premium_budget_allows() or force_critical
      if verdict == "GO" and conviction == "high" and sev in ("mild", "hard"):
        return self.premium_budget_allows()
      return False

    if purpose == "self_improvement":
      if metrics_poor or sev == "hard" or force_critical:
        return self.premium_budget_allows() or force_critical
      return False

    return False

  def summary(self) -> Dict[str, Any]:
    state = self._state()
    cheap = int(state.get("cheap", 0))
    premium = int(state.get("premium", 0))
    total = cheap + premium
    return {
      "date": self._day,
      "cheap_calls": cheap,
      "premium_calls": premium,
      "total_calls": total,
      "cheap_ratio": round(self.cheap_ratio(), 3) if total else 1.0,
      "premium_share": round(self.premium_share(), 3) if total else 0.0,
      "target_cheap_ratio": cheap_target_ratio(),
      "premium_budget_allows": self.premium_budget_allows(),
      "governor_enabled": governor_enabled(),
      "premium_escalation": premium_escalation_mode(),
    }


_governor: Optional[ModelBudgetGovernor] = None


def reset_governor() -> None:
  """Reset singleton and daily counters — use in tests."""
  global _governor
  _governor = None
  ModelBudgetGovernor._daily.clear()


def get_governor() -> ModelBudgetGovernor:
  global _governor
  if _governor is None:
    _governor = ModelBudgetGovernor()
  return _governor


def record_model_call(tier: str, model: str = "") -> None:
  if governor_enabled():
    get_governor().record_call(tier, model)


def should_escalate_to_premium(
  purpose: Purpose,
  **kwargs: Any,
) -> bool:
  return get_governor().should_escalate_to_premium(purpose, **kwargs)


def cheap_workhorse_route() -> Tuple[str, str, str, str, int]:
  """Single cheapest route for routine tasks."""
  from engine.llm_task_router import max_output_for_task, provider_for_task

  model = workhorse_model()
  task = "workhorse"
  max_out = max_output_for_task(task)
  provider = provider_for_task(task, model)
  return provider, model, "cheap", task, max_out


def limit_cheap_routes(
  routes: List[Tuple[str, str, str, Any, int]],
  *,
  max_routes: Optional[int] = None,
) -> List[Tuple[str, str, str, Any, int]]:
  """Cap parallel cheap routes to control token spend."""
  cap = max_routes
  if cap is None:
    cap = int(os.environ.get("EW_CHEAP_PARALLEL_MAX", "4"))
  cheap = [r for r in routes if r[2] == "cheap"]
  other = [r for r in routes if r[2] != "cheap"]
  return cheap[:cap] + other


def purpose_for_brain_domain(domain: str) -> Purpose:
  mapping = {
    "tv_oss": "routine",
    "tv_oss_discovery": "routine",
    "social": "routine",
    "risk": "self_improvement",
    "executive": "executive",
    "pr": "screen",
  }
  return mapping.get(domain, "routine")  # type: ignore[return-value]


def llm_allowed_for_routine() -> bool:
  """Whether routine consensus tasks may call LLM at all."""
  return routine_llm_enabled()


def governor_summary() -> Dict[str, Any]:
  return get_governor().summary()
