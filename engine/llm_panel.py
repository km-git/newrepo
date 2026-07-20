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
)
from engine.llm_model_roster import MODEL, disagreement_severity
from engine.llm_task_router import (
  CURSOR_FABLE,
  CURSOR_OPUS,
  CURSOR_SOL,
  screen_routes,
  tiebreaker_route,
  tiebreaker_task,
)
from engine.llm_backend import llm_backend
from engine.llm_cursor import cursor_available, cursor_model_for

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
  if mode == "ensemble" and llm_backend() == "cursor" and cursor_available():
    return "ensemble"
  if mode == "ensemble" and not _has_both_keys():
    return "single"
  return mode


def cheap_screen_routes(verdict: str, conviction: str = "") -> List[Tuple[Provider, str, str]]:
  """Always cheap tier — workhorse (single) or dual screen (ensemble)."""
  mode = effective_intelligence_mode()
  return [(p, m, t) for p, m, t, _task, _out in screen_routes(mode)]


def screen_route_details(verdict: str, conviction: str = "") -> List[tuple]:
  """Full route tuples including task + max_output for panel execution."""
  return screen_routes(effective_intelligence_mode())


def tiebreaker_routes(verdict: str, conviction: str = "") -> List[Tuple[Provider, str, str]]:
  """Premium escalation — executive / planning / tiebreaker by verdict."""
  route = tiebreaker_route(verdict, conviction)
  if not route:
    return []
  p, m, t, _task, _out = route
  return [(p, m, t)]


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
    trade["panel_warning"] = "LLM panel recommends reject — consider skip or reduced size."
  elif stance == "caution":
    trade["panel_note"] = "Mixed model consensus — verify wave count before sizing up."

  return trade


def run_panel(
  prompt: str,
  verdict: str,
  conviction: str,
  call_provider: Callable[..., dict],
) -> dict:
  """
  Execute intelligence panel:
  1. Cheap screen (parallel when 2+ routes)
  2. Premium tiebreaker on disagreement (ensemble only)
  """
  mode = effective_intelligence_mode()
  screen_detail = screen_route_details(verdict, conviction)
  responses: Dict[str, dict] = {}

  def _invoke(route: tuple) -> Tuple[str, dict]:
    provider, model, tier, task, max_out = route
    return provider, call_provider(provider, model, tier, task, max_out)

  if len(screen_detail) > 1:
    with ThreadPoolExecutor(max_workers=len(screen_detail)) as pool:
      futures = {pool.submit(_invoke, r): r for r in screen_detail}
      for fut in as_completed(futures):
        provider, resp = fut.result()
        responses[provider] = resp
  else:
    for route in screen_detail:
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
  tiebreaker_route_meta: Optional[dict] = None
  escalated = False

  stances = _stance_values(ok_screen)
  severity = disagreement_severity(stances)

  if mode == "ensemble" and models_disagree(ok_screen):
    tb = tiebreaker_route(verdict, conviction, stances=stances)
    if tb:
      escalated = True
      provider, model, tier, task, max_out = tb
      tiebreaker_route_meta = {
        "provider": provider,
        "model": model,
        "tier": tier,
        "task": task,
        "disagreement_severity": severity,
      }
      tiebreaker = call_provider(provider, model, tier, task, max_out)
      tiebreaker["role"] = task

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
      "routes": [
        {"provider": p, "model": m, "tier": t, "task": task, "max_output": out}
        for p, m, t, task, out in screen_detail
      ],
    },
    "disagreement": models_disagree(ok_screen),
    "disagreement_severity": severity if models_disagree(ok_screen) else "none",
    "escalated_to_premium": escalated,
    "tiebreaker": tiebreaker,
    "tiebreaker_route": tiebreaker_route_meta if escalated else None,
    "tiebreaker_task": tiebreaker_task(verdict, conviction, stances) if escalated else None,
    "consensus_stance": consensus,
    "confidence_adjustment": conf_adj,
    "consulted": consulted,
    "models_used": {
      "cheap_openai": cursor_model_for("openai", "cheap") if llm_backend() == "cursor" else CHEAP_OPENAI,
      "cheap_anthropic": cursor_model_for("anthropic", "cheap") if llm_backend() == "cursor" else CHEAP_ANTHROPIC,
      "crucial_opus": CURSOR_OPUS,
      "crucial_fable": CURSOR_FABLE,
      "crucial_sol": CURSOR_SOL,
      "mild_tiebreaker": MODEL["mild_tb"],
      "grok_high": MODEL["grok_high"],
      "light_planning": MODEL["light_plan"],
      "backend": llm_backend(),
    },
  }
  if summaries:
    result["blended_summary"] = " | ".join(summaries)
  return result
