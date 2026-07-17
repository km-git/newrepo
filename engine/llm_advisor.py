"""Second-opinion advisory from Claude + GPT on critical trade decisions (token-efficient)."""

from __future__ import annotations

import json
import os
import urllib.error
import urllib.request
from typing import Any, Dict, List, Optional

from cache.disk_cache import get_cache
from engine.llm_token_router import (
  DEFAULT_MAX_OUTPUT_TOKENS,
  SYSTEM_PROMPT,
  build_compact_prompt,
  compact_advisory_payload,
  routing_plan,
  select_providers,
  token_budget_report,
)
from engine.llm_panel import (
  apply_panel_to_trade,
  cheap_screen_routes,
  effective_intelligence_mode,
  run_panel,
)
from engine.llm_cost import attach_cost_estimate

NAMESPACE = "llm_advisory"
CRITICAL_VERDICTS = frozenset({"GO", "CONDITIONAL_GO"})


def advisory_enabled(explicit: Optional[bool] = None) -> bool:
  if explicit is not None:
    return explicit
  return os.environ.get("EW_LLM_ADVISORY", "").lower() in ("1", "true", "yes")


def is_critical_decision(verdict: str, outcomes: Optional[dict] = None) -> bool:
  if verdict in CRITICAL_VERDICTS:
    return True
  if not outcomes:
    return False
  hs = outcomes.get("honest_summary") or {}
  if hs.get("full_executable_count", 0) > 0:
    return True
  if hs.get("probe_executable_count", 0) > 0 and verdict == "STAGED_GO":
    return True
  return False


def build_advisory_prompt(
  symbol: str,
  executive: dict,
  trade_setup: dict,
  wave_structure: dict,
  consensus: dict,
  outcomes: dict,
  market_tools: Optional[dict] = None,
) -> str:
  """Compact prompt — ~60% fewer input tokens vs indented JSON block."""
  payload = compact_advisory_payload(
    symbol, executive, trade_setup, wave_structure, consensus, outcomes, market_tools
  )
  return build_compact_prompt(payload)


def _http_post(url: str, headers: dict, body: dict, timeout: int = 45) -> dict:
  data = json.dumps(body).encode()
  req = urllib.request.Request(url, data=data, headers=headers, method="POST")
  with urllib.request.urlopen(req, timeout=timeout) as resp:
    return json.loads(resp.read().decode())


def _parse_json_response(text: str) -> dict:
  text = text.strip()
  if text.startswith("```"):
    text = text.split("```", 2)[1]
    if text.startswith("json"):
      text = text[4:]
  return json.loads(text.strip())


def call_openai_advisory(prompt: str, model: str) -> dict:
  key = os.environ.get("OPENAI_API_KEY", "").strip()
  if not key:
    return {"available": False, "error": "OPENAI_API_KEY not set"}
  try:
    raw = _http_post(
      "https://api.openai.com/v1/chat/completions",
      {"Authorization": f"Bearer {key}", "Content-Type": "application/json"},
      {
        "model": model,
        "temperature": 0.2,
        "max_tokens": DEFAULT_MAX_OUTPUT_TOKENS,
        "response_format": {"type": "json_object"},
        "messages": [
          {"role": "system", "content": SYSTEM_PROMPT},
          {"role": "user", "content": prompt.split("\n\nDATA:", 1)[-1] if "DATA:" in prompt else prompt},
        ],
      },
    )
    content = raw["choices"][0]["message"]["content"]
    usage = raw.get("usage") or {}
    parsed = _parse_json_response(content)
    return {
      "available": True,
      "model": model,
      "provider": "openai",
      "usage": usage,
      **parsed,
    }
  except (urllib.error.URLError, KeyError, json.JSONDecodeError, IndexError) as e:
    return {"available": True, "provider": "openai", "model": model, "error": str(e)}


def call_anthropic_advisory(prompt: str, model: str) -> dict:
  key = os.environ.get("ANTHROPIC_API_KEY", "").strip()
  if not key:
    return {"available": False, "error": "ANTHROPIC_API_KEY not set"}
  user_content = prompt.split("\n\nDATA:", 1)[-1] if "DATA:" in prompt else prompt
  try:
    raw = _http_post(
      "https://api.anthropic.com/v1/messages",
      {
        "x-api-key": key,
        "anthropic-version": "2023-06-01",
        "Content-Type": "application/json",
      },
      {
        "model": model,
        "max_tokens": DEFAULT_MAX_OUTPUT_TOKENS,
        "temperature": 0.2,
        "system": [
          {
            "type": "text",
            "text": SYSTEM_PROMPT,
            "cache_control": {"type": "ephemeral"},
          }
        ],
        "messages": [{"role": "user", "content": user_content}],
      },
    )
    content = raw["content"][0]["text"]
    usage = raw.get("usage") or {}
    parsed = _parse_json_response(content)
    return {
      "available": True,
      "model": model,
      "provider": "anthropic",
      "usage": usage,
      **parsed,
    }
  except (urllib.error.URLError, KeyError, json.JSONDecodeError, IndexError) as e:
    return {"available": True, "provider": "anthropic", "model": model, "error": str(e)}


def _blend_stances(responses: List[dict]) -> str:
  stances = [r.get("stance") for r in responses if r.get("stance")]
  if not stances:
    return "unknown"
  if any(s == "reject" for s in stances):
    return "reject"
  if all(s == "agree" for s in stances):
    return "agree"
  return "caution"


def get_llm_advisory(
  symbol: str,
  executive: dict,
  trade_setup: dict,
  wave_structure: dict,
  consensus: dict,
  outcomes: dict,
  market_tools: Optional[dict] = None,
  use_cache: bool = True,
) -> dict:
  verdict = executive.get("verdict", "")
  conviction = executive.get("conviction", "")
  price = round(float(trade_setup.get("entry_zone", [0])[0] if trade_setup.get("entry_zone") else 0), 0)
  mode = effective_intelligence_mode()
  routes = cheap_screen_routes(verdict, conviction) if mode in ("ensemble", "dual") else routing_plan(verdict, conviction)
  cache_key = (mode, symbol, verdict, executive.get("direction"), price, tuple((p, m) for p, m, _ in routes))

  if use_cache:
    cached = get_cache().get(NAMESPACE, *cache_key)
    if cached is not None:
      cached = dict(cached)
      cached["cache_hit"] = True
      if cached.get("token_budget"):
        cached["token_budget"]["cache_hit"] = True
      return cached

  prompt = build_advisory_prompt(
    symbol, executive, trade_setup, wave_structure, consensus, outcomes, market_tools
  )
  budget = token_budget_report(prompt, routes)
  budget["intelligence_mode"] = mode

  if mode in ("ensemble", "dual"):

    def _call_provider(provider: str, model: str, tier: str) -> dict:
      if provider == "openai":
        return call_openai_advisory(prompt, model)
      return call_anthropic_advisory(prompt, model)

    panel = run_panel(prompt, verdict, conviction, _call_provider)
    responses = panel["screen"]
    result = {
      "critical": True,
      "consulted": panel["consulted"],
      "openai": responses["openai"],
      "anthropic": responses["anthropic"],
      "consensus_stance": panel["consensus_stance"],
      "confidence_adjustment": panel.get("confidence_adjustment"),
      "intelligence_panel": panel,
      "intelligence_mode": mode,
      "cache_hit": False,
      "token_budget": budget,
    }
    if panel.get("blended_summary"):
      result["blended_summary"] = panel["blended_summary"]
    if panel.get("confidence_adjustment") is not None:
      result["avg_confidence_adjustment"] = panel["confidence_adjustment"]
    if panel.get("escalated_to_premium"):
      tb = panel.get("tiebreaker_route") or {}
      budget["routes"].append(tb)
      budget["est_total_tokens"] += budget.get("max_output_tokens", DEFAULT_MAX_OUTPUT_TOKENS)
    tb_route = None
    if panel.get("tiebreaker_route"):
      tr = panel["tiebreaker_route"]
      tb_route = (tr["provider"], tr["model"], tr["tier"])
    budget = attach_cost_estimate(
      budget,
      routes,
      escalated=bool(panel.get("escalated_to_premium")),
      tiebreaker_route=tb_route,
    )
    panel["cost_estimate"] = budget.get("cost_estimate")
    result["token_budget"] = budget
  else:
    responses: Dict[str, dict] = {}
    for provider, model, tier in routes:
      if provider == "openai":
        responses["openai"] = call_openai_advisory(prompt, model)
      else:
        responses["anthropic"] = call_anthropic_advisory(prompt, model)

    if "openai" not in responses:
      responses["openai"] = {"available": False, "error": "not selected (EW_LLM_INTELLIGENCE=single)"}
    if "anthropic" not in responses:
      responses["anthropic"] = {"available": False, "error": "not selected (EW_LLM_INTELLIGENCE=single)"}

    consulted = []
    ok_responses = []
    for label in ("openai", "anthropic"):
      resp = responses[label]
      if resp.get("available") and resp.get("stance"):
        consulted.append(label)
        ok_responses.append(resp)

    result = {
      "critical": True,
      "consulted": consulted,
      "openai": responses["openai"],
      "anthropic": responses["anthropic"],
      "consensus_stance": _blend_stances(ok_responses),
      "cache_hit": False,
      "token_budget": budget,
      "intelligence_mode": mode,
    }

    summaries = [r.get("summary") for r in ok_responses if r.get("summary")]
    if summaries:
      result["blended_summary"] = " | ".join(summaries)

    adjustments = [
      r.get("confidence_adjustment")
      for r in ok_responses
      if isinstance(r.get("confidence_adjustment"), (int, float))
    ]
    if adjustments:
      adj = round(sum(adjustments) / len(adjustments), 3)
      result["avg_confidence_adjustment"] = adj
      result["confidence_adjustment"] = adj

    budget = attach_cost_estimate(budget, routes)
    result["token_budget"] = budget

  consulted = result.get("consulted") or []
  if not consulted:
    if not select_providers():
      result["skipped_reason"] = "No API keys (OPENAI_API_KEY or ANTHROPIC_API_KEY)"
    else:
      result["skipped_reason"] = "Consultation failed — check API errors in openai/anthropic fields"
    print(f"[llm] advisory skipped for {symbol}: {result['skipped_reason']}")
  else:
    escalated = (result.get("intelligence_panel") or {}).get("escalated_to_premium", False)
    cost = (result.get("token_budget") or {}).get("cost_estimate", {}).get("est_total_usd")
    cost_s = f" ~${cost:.5f}" if isinstance(cost, (int, float)) else ""
    print(
      f"[llm] advisory {symbol}: mode={mode} consulted={consulted} "
      f"stance={result['consensus_stance']} escalated={escalated} "
      f"~{budget['est_total_tokens']}tok{cost_s}"
    )

  if use_cache and consulted:
    get_cache().set(NAMESPACE, result, *cache_key)

  return result


def maybe_advise_critical(
  *,
  symbol: str,
  executive: dict,
  trade_setup: dict,
  wave_structure: dict,
  consensus: dict,
  outcomes: dict,
  market_tools: Optional[dict] = None,
  enabled: bool = False,
) -> Optional[dict]:
  if not enabled:
    return None
  if not is_critical_decision(executive.get("verdict", ""), outcomes):
    return None
  return get_llm_advisory(
    symbol, executive, trade_setup, wave_structure, consensus, outcomes, market_tools
  )
