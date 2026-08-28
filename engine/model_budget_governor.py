"""
Model budget governor — 98% Cursor Pro, max 2% Other Models (ashamed above 2%, hard stop at 5%).

Other Models (GPT/Claude/Gemini) are a last resort for executive GO + high conviction +
hard disagreement only. Using them beyond 2% daily share is tracked as shame events.
Hard ceiling at 5% — never exceeded regardless of outcome pressure.
"""

from __future__ import annotations

import os
from datetime import date
from typing import Any, Dict, List, Literal, Optional, Tuple

from engine.llm_model_roster import MODEL, ROSTER, disagreement_severity, workhorse_model

Purpose = Literal["routine", "screen", "self_improvement", "executive", "research"]

CHEAP_TIERS = frozenset({"nano", "workhorse", "cheap"})
PREMIUM_TIERS = frozenset({"standard", "crucial", "flagship", "premium"})

# Cursor Pro included models — never count against Other Models quota
CURSOR_PRO_MODELS = frozenset({
  "composer-2.5",
  "grok-4.5",
  "cursor-grok-4.5-high",
})

# Map Other Models → best Cursor Pro substitute when quota exhausted
CURSOR_SUBSTITUTE: Dict[str, str] = {
  "gpt-5.4-nano": "composer-2.5",
  "gpt-5-mini": "composer-2.5",
  "gpt-5.6-luna": "cursor-grok-4.5-high",
  "gpt-5.6-terra": "cursor-grok-4.5-high",
  "gpt-5.6-sol": "cursor-grok-4.5-high",
  "claude-4.5-sonnet": "cursor-grok-4.5-high",
  "claude-opus-4-8": "cursor-grok-4.5-high",
  "claude-fable-5": "cursor-grok-4.5-high",
  "gemini-3-flash": "grok-4.5",
}


def cheap_target_ratio() -> float:
  """Target fraction of LLM calls on cheap tiers (default 90%)."""
  return float(os.environ.get("EW_CHEAP_MODEL_RATIO", "0.90"))


def cursor_target_ratio() -> float:
  """Target fraction of calls on Cursor Pro models (default 98%)."""
  return float(os.environ.get("EW_CURSOR_MODEL_RATIO", "0.98"))


def other_model_target_max() -> float:
  """Target max Other Models share — ashamed to exceed (default 2%)."""
  return float(os.environ.get("EW_OTHER_MODEL_TARGET_MAX", "0.02"))


def other_model_hard_ceiling() -> float:
  """Absolute hard stop for Other Models share (default 5%, never exceed)."""
  return float(os.environ.get("EW_OTHER_MODEL_HARD_CEILING", "0.05"))


def min_cursor_calls_before_other() -> int:
  """Cursor Pro calls required before first Other Model (default 50 ≈ 2% budget)."""
  return int(os.environ.get("EW_MIN_CURSOR_CALLS_BEFORE_OTHER", "50"))


def other_models_executive_only() -> bool:
  """When true, GPT/Claude/Gemini only for executive purpose (default on)."""
  return os.environ.get("EW_OTHER_MODELS_EXECUTIVE_ONLY", "1").lower() not in ("0", "false", "no")


def other_model_pool_enabled() -> bool:
  """Allow Other Models when executive budget permits (default on, capped at 2%)."""
  return os.environ.get("EW_USE_OTHER_MODEL_POOL", "1").lower() not in ("0", "false", "no")


def premium_escalation_mode() -> str:
  """smart (default) | always | never"""
  return os.environ.get("EW_PREMIUM_ESCALATION", "smart").lower().strip()


def governor_enabled() -> bool:
  return os.environ.get("EW_MODEL_BUDGET_GOVERNOR", "1").lower() not in ("0", "false", "no")


def cursor_pool_governor_enabled() -> bool:
  return os.environ.get("EW_CURSOR_POOL_GOVERNOR", "1").lower() not in ("0", "false", "no")


def cursor_only_screen() -> bool:
  """Dual screen uses only Cursor Pro models (no GPT-mini slot)."""
  return os.environ.get("EW_CURSOR_ONLY_SCREEN", "1").lower() not in ("0", "false", "no")


def routine_llm_enabled() -> bool:
  """Routine consensus (TV OSS, social) — off by default to save tokens."""
  return os.environ.get("EW_ROUTINE_LLM", "0").lower() in ("1", "true", "yes")


def is_cursor_pro_model(model_id: str) -> bool:
  """True for Composer/Grok models included in Cursor Pro."""
  if not model_id:
    return False
  if model_id in CURSOR_PRO_MODELS:
    return True
  meta = ROSTER.get(model_id, {})
  return meta.get("pool") == "first_party" or meta.get("family") == "cursor"


def is_other_model(model_id: str) -> bool:
  """True for GPT/Claude/Gemini API pool models (consumes Other Models quota)."""
  if not model_id or is_cursor_pro_model(model_id):
    return False
  meta = ROSTER.get(model_id, {})
  return meta.get("pool") == "api" or meta.get("family") in ("openai", "anthropic", "google")


def cursor_substitute_for(model_id: str) -> str:
  """Best Cursor Pro replacement for an Other Model."""
  if is_cursor_pro_model(model_id):
    return model_id
  return CURSOR_SUBSTITUTE.get(model_id, MODEL.get("grok_high", "cursor-grok-4.5-high"))


def _tier_is_cheap(tier: str) -> bool:
  return (tier or "cheap").lower() in CHEAP_TIERS


def _roster_tier(model_id: str) -> str:
  return str((ROSTER.get(model_id) or {}).get("tier", "workhorse"))


class ModelBudgetGovernor:
  """Daily cheap/premium + cursor/other call tracker."""

  _daily: Dict[str, Dict[str, int]] = {}

  def __init__(self) -> None:
    self._day = date.today().isoformat()

  def _state(self) -> dict:
    base = {"cheap": 0, "premium": 0, "cursor": 0, "other": 0, "shame_events": 0}
    stored = self._daily.get(self._day, {})
    base.update(stored)
    return base

  def _save(self, state: dict) -> None:
    self._daily[self._day] = state

  def record_call(self, tier: str, model: str = "") -> None:
    state = self._state()
    roster_tier = _roster_tier(model) if model else tier
    bucket = "cheap" if _tier_is_cheap(tier) or roster_tier in ("nano", "workhorse") else "premium"
    state[bucket] = int(state.get(bucket, 0)) + 1
    if model:
      pool_bucket = "cursor" if is_cursor_pro_model(model) else "other"
      state[pool_bucket] = int(state.get(pool_bucket, 0)) + 1
      if pool_bucket == "other":
        cursor = int(state.get("cursor", 0))
        other = int(state.get("other", 0))
        total = cursor + other
        if total > 0 and (other / total) > other_model_target_max() + 0.001:
          state["shame_events"] = int(state.get("shame_events", 0)) + 1
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

  def cursor_ratio(self) -> float:
    state = self._state()
    cursor = int(state.get("cursor", 0))
    other = int(state.get("other", 0))
    total = cursor + other
    if total == 0:
      return 1.0
    return cursor / total

  def other_share(self) -> float:
    return 1.0 - self.cursor_ratio()

  def is_ashamed(self) -> bool:
    """True when Other Models share exceeds 2% target — ashamed to use them."""
    if not cursor_pool_governor_enabled():
      return False
    state = self._state()
    cursor = int(state.get("cursor", 0))
    other = int(state.get("other", 0))
    total = cursor + other
    if total == 0:
      return False
    return (other / total) > other_model_target_max() + 0.001

  def premium_budget_allows(self) -> bool:
    if not governor_enabled():
      return True
    if premium_escalation_mode() == "never":
      return False
    if premium_escalation_mode() == "always":
      return True
    max_premium = 1.0 - cheap_target_ratio()
    return self.premium_share() < max_premium + 0.001

  def other_model_budget_allows(self) -> bool:
    """True only when projected Other share stays ≤2% and below 5% hard ceiling."""
    if not cursor_pool_governor_enabled():
      return other_model_pool_enabled()
    if not other_model_pool_enabled():
      return False
    state = self._state()
    cursor = int(state.get("cursor", 0))
    other = int(state.get("other", 0))
    total = cursor + other
    if total == 0 or cursor < min_cursor_calls_before_other():
      return False
    current_share = other / total if total else 0.0
    if current_share >= other_model_hard_ceiling():
      return False
    projected_share = (other + 1) / (total + 1)
    if projected_share > other_model_hard_ceiling():
      return False
    return projected_share <= other_model_target_max() + 0.001

  def should_use_other_model(
    self,
    purpose: Purpose,
    *,
    verdict: str = "",
    conviction: str = "",
    stances: Optional[List[str]] = None,
    force_critical: bool = False,
  ) -> bool:
    """
    Gate Other Models — only executive GO + high conviction + hard disagreement.
    Ashamed to use beyond 2%; hard blocked at 5%.
    """
    if not other_model_pool_enabled():
      return False
    if other_models_executive_only() and purpose != "executive":
      return False
    if self.is_ashamed():
      return False
    sev = disagreement_severity(stances or [])
    if not (
      force_critical
      and verdict == "GO"
      and conviction == "high"
      and sev == "hard"
    ):
      return False
    if not cursor_pool_governor_enabled():
      return True
    return self.other_model_budget_allows()

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

    return False

  def summary(self) -> Dict[str, Any]:
    state = self._state()
    cheap = int(state.get("cheap", 0))
    premium = int(state.get("premium", 0))
    cursor = int(state.get("cursor", 0))
    other = int(state.get("other", 0))
    pool_total = cursor + other
    tier_total = cheap + premium
    return {
      "date": self._day,
      "cheap_calls": cheap,
      "premium_calls": premium,
      "total_calls": tier_total,
      "cheap_ratio": round(self.cheap_ratio(), 3) if tier_total else 1.0,
      "premium_share": round(self.premium_share(), 3) if tier_total else 0.0,
      "target_cheap_ratio": cheap_target_ratio(),
      "cursor_calls": cursor,
      "other_calls": other,
      "cursor_ratio": round(self.cursor_ratio(), 3) if pool_total else 1.0,
      "other_share": round(self.other_share(), 3) if pool_total else 0.0,
      "target_cursor_ratio": cursor_target_ratio(),
      "other_model_target_max": other_model_target_max(),
      "other_model_hard_ceiling": other_model_hard_ceiling(),
      "other_model_ashamed": self.is_ashamed(),
      "shame_events": int(state.get("shame_events", 0)),
      "min_cursor_before_other": min_cursor_calls_before_other(),
      "other_model_budget_allows": self.other_model_budget_allows(),
      "premium_budget_allows": self.premium_budget_allows(),
      "governor_enabled": governor_enabled(),
      "cursor_pool_governor": cursor_pool_governor_enabled(),
      "other_model_pool_enabled": other_model_pool_enabled(),
      "other_models_executive_only": other_models_executive_only(),
      "premium_escalation": premium_escalation_mode(),
    }


_governor: Optional[ModelBudgetGovernor] = None


def reset_governor() -> None:
  global _governor
  _governor = None
  ModelBudgetGovernor._daily.clear()


def get_governor() -> ModelBudgetGovernor:
  global _governor
  if _governor is None:
    _governor = ModelBudgetGovernor()
  return _governor


def record_model_call(tier: str, model: str = "") -> None:
  if governor_enabled() or cursor_pool_governor_enabled():
    get_governor().record_call(tier, model)


def should_escalate_to_premium(purpose: Purpose, **kwargs: Any) -> bool:
  return get_governor().should_escalate_to_premium(purpose, **kwargs)


def should_use_other_model(purpose: Purpose, **kwargs: Any) -> bool:
  return get_governor().should_use_other_model(purpose, **kwargs)


def other_model_shame_status() -> Dict[str, Any]:
  """Report whether we should be ashamed of Other Models usage today."""
  g = get_governor()
  share = g.other_share()
  return {
    "ashamed": g.is_ashamed(),
    "other_share": round(share, 4),
    "target_max": other_model_target_max(),
    "hard_ceiling": other_model_hard_ceiling(),
    "shame_events": g._state().get("shame_events", 0),
    "message": (
      "Other Models over 2% target — use Cursor Pro"
      if g.is_ashamed()
      else "Within 2% Other Models budget"
    ),
  }


def purpose_from_task(task: str) -> Purpose:
  """Map LLM task → budget purpose. Only task=executive may use Other Models."""
  if task == "executive":
    return "executive"
  if task in ("architect", "synthesis", "planning", "tiebreaker"):
    return "self_improvement"
  if task in ("screen", "workhorse"):
    return "screen"
  return "routine"


def prefer_cursor_pool_model(
  model_id: str,
  *,
  purpose: Purpose = "routine",
  force_critical: bool = False,
) -> Tuple[str, bool]:
  """
  Return (model, substituted).
  Substitutes Other Models with Cursor Pro when pool budget is exhausted or disabled.
  """
  if is_cursor_pro_model(model_id):
    return model_id, False
  if not is_other_model(model_id):
    return model_id, False
  if should_use_other_model(purpose, force_critical=force_critical):
    return model_id, False
  sub = cursor_substitute_for(model_id)
  return sub, sub != model_id


def route_model_for_task(
  model_id: str,
  tier: str,
  *,
  purpose: Purpose = "routine",
  force_critical: bool = False,
) -> Tuple[str, str, bool]:
  """Apply cursor pool preference; returns (model, tier, substituted)."""
  model, substituted = prefer_cursor_pool_model(
    model_id, purpose=purpose, force_critical=force_critical,
  )
  if substituted and tier == "premium":
    tier = "standard"
  return model, tier, substituted


def cheap_workhorse_route() -> Tuple[str, str, str, str, int]:
  from engine.llm_task_router import max_output_for_task, provider_for_task

  model = workhorse_model()
  model, _ = prefer_cursor_pool_model(model, purpose="routine")
  task = "workhorse"
  max_out = max_output_for_task(task)
  provider = provider_for_task(task, model)
  return provider, model, "cheap", task, max_out


def limit_cheap_routes(
  routes: List[Tuple[str, str, str, Any, int]],
  *,
  max_routes: Optional[int] = None,
) -> List[Tuple[str, str, str, Any, int]]:
  cap = max_routes
  if cap is None:
    cap = int(os.environ.get("EW_CHEAP_PARALLEL_MAX", "4"))
  cheap = [r for r in routes if r[2] == "cheap"]
  other = [r for r in routes if r[2] != "cheap"]
  return cheap[:cap] + other


def filter_routes_to_cursor_pro(
  routes: List[Tuple[str, str, str, Any, int]],
  *,
  purpose: Purpose = "routine",
) -> List[Tuple[str, str, str, Any, int]]:
  """Drop or substitute routes that would consume Other Models quota."""
  out: List[Tuple[str, str, str, Any, int]] = []
  for provider, model, tier, task, max_out in routes:
    if is_other_model(model) and not should_use_other_model(purpose):
      model, tier, _ = route_model_for_task(model, tier, purpose=purpose)
      tier = "cheap" if tier in ("nano", "workhorse") else tier
    out.append((provider, model, tier, task, max_out))
  return out


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
  return routine_llm_enabled()


def governor_summary() -> Dict[str, Any]:
  return get_governor().summary()
