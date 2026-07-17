"""Multi-model intelligence panel — cheap dual screen, premium tiebreaker on disagreement."""

from __future__ import annotations

import os
from concurrent.futures import ThreadPoolExecutor, as_completed
from typing import Callable, Dict, List, Literal, Optional, Tuple

from engine.llm_token_router import (
  CHEAP_ANTHROPIC,
  CHEAP_OPENAI,
  STANDARD_ANTHROPIC,
  STANDARD_OPENAI,
  Provider,
  model_for,
  tier_for_verdict,
)

IntelligenceMode = Literal["ensemble", "single", "dual"]
Stance = Literal["agree", "caution", "reject", "unknown"]

STANCE_RANK = {"reject": 0, "caution": 1, "agree": 2, "unknown": -1}


def intelligence_mode() -> IntelligenceMode:
  """
  How to combine models when --llm-advisory is on:
  - ensemble (default): cheap dual screen + premium tiebreaker on disagreement
  - single: one cheap model (token-minimal)
  - dual: both cheap models, no tiebreaker
  """
  raw = os.environ.get("EW_LLM_INTELLIGENCE", "ensemble").lower().strip()
  if raw in ("ensemble", "single", "dual"):
    return raw  # type: ignore[return-value]
  return "ensemble"


def _has_both_keys() -> bool:
  return bool(os.environ.get("OPENAI_API_KEY", "").strip()) and bool(
    os.environ.get("ANTHROPIC_API_KEY", "").strip()
  )


def effective_intelligence_mode() -> IntelligenceMode:
  mode = intelligence_mode()
  if mode == "ensemble" and not _has_both_keys():
    return "single"
  return mode


def cheap_screen_routes(verdict: str, conviction: str = "") -> List[Tuple[Provider, str, str]]:
  """Always use cheap tier for the initial screen."""
  tier = "cheap"
  mode = effective_intelligence_mode()

  if mode == "single":
    providers: List[Provider] = []
    if os.environ.get("OPENAI_API_KEY", "").strip():
      providers.append("openai")
    elif os.environ.get("ANTHROPIC_API_KEY", "").strip():
      providers.append("anthropic")
    return [(providers[0], model_for(providers[0], tier), tier)] if providers else []
  if mode in ("ensemble", "dual"):
    # Force both providers when keys exist
    routes: List[Tuple[Provider, str, str]] = []
    if os.environ.get("OPENAI_API_KEY", "").strip():
      routes.append(("openai", model_for("openai", tier), tier))
    if os.environ.get("ANTHROPIC_API_KEY", "").strip():
      routes.append(("anthropic", model_for("anthropic", tier), tier))
    return routes
  return [(p, model_for(p, tier), tier) for p in providers]


def tiebreaker_routes(verdict: str, conviction: str = "") -> List[Tuple[Provider, str, str]]:
  """One premium model to break disagreement — OpenAI preferred."""
  tier = tier_for_verdict(verdict, conviction)
  if tier == "cheap":
    tier = "standard"
  if os.environ.get("OPENAI_API_KEY", "").strip():
    return [("openai", model_for("openai", tier), tier)]
  if os.environ.get("ANTHROPIC_API_KEY", "").strip():
    return [("anthropic", model_for("anthropic", tier), tier)]
  return []


def _stance_values(responses: List[dict]) -> List[str]:
  return [r.get("stance") for r in responses if r.get("stance")]


def models_disagree(responses: List[dict]) -> bool:
  """True when cheap models materially disagree (not unanimous)."""
  stances = _stance_values(responses)
  if len(stances) < 2:
    return False
  unique = set(stances)
  if unique == {"agree"}:
    return False
  if "reject" in unique and "agree" in unique:
    return True
  if len(unique) >= 2:
    return True
  return False


def blend_stances(responses: List[dict], tiebreaker: Optional[dict] = None) -> Stance:
  """Consensus stance — tiebreaker wins when present."""
  if tiebreaker and tiebreaker.get("stance"):
    return tiebreaker["stance"]  # type: ignore[return-value]
  stances = _stance_values(responses)
  if not stances:
    return "unknown"
  if any(s == "reject" for s in stances):
    return "reject"
  if all(s == "agree" for s in stances):
    return "agree"
  return "caution"


def avg_confidence_adjustment(responses: List[dict], tiebreaker: Optional[dict] = None) -> Optional[float]:
  pool = list(responses)
  if tiebreaker and isinstance(tiebreaker.get("confidence_adjustment"), (int, float)):
    pool.append(tiebreaker)
  adjustments = [
    r.get("confidence_adjustment")
    for r in pool
    if isinstance(r.get("confidence_adjustment"), (int, float))
  ]
  if not adjustments:
    return None
  return round(sum(adjustments) / len(adjustments), 3)


def apply_panel_to_trade(trade_setup: dict, panel: dict) -> dict:
  """
  Adjust trade confidence from panel — never silently override executive verdict.
  Returns updated trade_setup copy + panel audit fields.
  """
  trade = dict(trade_setup)
  adj = panel.get("confidence_adjustment")
  if not isinstance(adj, (int, float)):
    return trade

  base = float(trade.get("confidence") or 0.5)
  new_conf = max(0.0, min(0.85, round(base + adj, 3)))
  trade["confidence"] = new_conf
  trade["confidence_before_panel"] = base
  trade["panel_confidence_adjustment"] = adj

  stance = panel.get("consensus_stance")
  if stance == "reject":
    trade["panel_warning"] = "LLM panel recommends caution — consider reduced size or skip."
  elif stance == "caution":
    trade["panel_note"] = "Mixed model consensus — verify wave count before sizing up."

  return trade


def run_panel(
  prompt: str,
  verdict: str,
  conviction: str,
  call_provider: Callable[[Provider, str, str], dict],
) -> dict:
  """
  Execute intelligence panel:
  1. Cheap screen (parallel when 2+ routes)
  2. Premium tiebreaker on disagreement (ensemble only)
  """
  mode = effective_intelligence_mode()
  screen_routes = cheap_screen_routes(verdict, conviction)
  responses: Dict[str, dict] = {}

  def _invoke(route: Tuple[Provider, str, str]) -> Tuple[str, dict]:
    provider, model, tier = route
    return provider, call_provider(provider, model, tier)

  if len(screen_routes) > 1:
    with ThreadPoolExecutor(max_workers=len(screen_routes)) as pool:
      futures = {pool.submit(_invoke, r): r for r in screen_routes}
      for fut in as_completed(futures):
        provider, resp = fut.result()
        responses[provider] = resp
  else:
    for route in screen_routes:
      provider, resp = _invoke(route)
      responses[provider] = resp

  for p in ("openai", "anthropic"):
    if p not in responses:
      responses[p] = {"available": False, "error": f"not in {mode} screen"}

  ok_screen = [
    responses[p]
    for p in ("openai", "anthropic")
    if responses[p].get("available") and responses[p].get("stance")
  ]

  tiebreaker: Optional[dict] = None
  tiebreaker_route: Optional[Tuple[Provider, str, str]] = None
  escalated = False

  if mode == "ensemble" and models_disagree(ok_screen):
    tb_routes = tiebreaker_routes(verdict, conviction)
    if tb_routes:
      escalated = True
      tiebreaker_route = tb_routes[0]
      provider, model, tier = tiebreaker_route
      tiebreaker = call_provider(provider, model, tier)
      tiebreaker["role"] = "tiebreaker"

  consensus = blend_stances(ok_screen, tiebreaker)
  conf_adj = avg_confidence_adjustment(ok_screen, tiebreaker)

  consulted = [p for p in ("openai", "anthropic") if responses[p].get("stance")]
  if tiebreaker and tiebreaker.get("stance"):
    consulted.append("tiebreaker")

  summaries = [r.get("summary") for r in ok_screen if r.get("summary")]
  if tiebreaker and tiebreaker.get("summary"):
    summaries.append(f"[tiebreaker] {tiebreaker['summary']}")

  result = {
    "intelligence_mode": mode,
    "screen": {
      "openai": responses["openai"],
      "anthropic": responses["anthropic"],
      "routes": [{"provider": p, "model": m, "tier": t} for p, m, t in screen_routes],
    },
    "disagreement": models_disagree(ok_screen),
    "escalated_to_premium": escalated,
    "tiebreaker": tiebreaker,
    "tiebreaker_route": (
      {"provider": tiebreaker_route[0], "model": tiebreaker_route[1], "tier": tiebreaker_route[2]}
      if tiebreaker_route
      else None
    ),
    "consensus_stance": consensus,
    "confidence_adjustment": conf_adj,
    "consulted": consulted,
    "models_used": {
      "cheap_openai": CHEAP_OPENAI,
      "cheap_anthropic": CHEAP_ANTHROPIC,
      "premium_openai": STANDARD_OPENAI,
      "premium_anthropic": STANDARD_ANTHROPIC,
    },
  }
  if summaries:
    result["blended_summary"] = " | ".join(summaries)
  return result
