"""Second-opinion advisory from Claude + GPT on critical trade decisions."""

from __future__ import annotations

import json
import os
import urllib.error
import urllib.request
from typing import Any, Dict, List, Optional

from cache.disk_cache import get_cache

CRITICAL_VERDICTS = frozenset({"GO", "CONDITIONAL_GO"})
DEFAULT_OPENAI_MODEL = os.environ.get("EW_OPENAI_MODEL", "gpt-4o-mini")
DEFAULT_ANTHROPIC_MODEL = os.environ.get("EW_ANTHROPIC_MODEL", "claude-sonnet-4-20250514")
NAMESPACE = "llm_advisory"


def advisory_enabled(explicit: Optional[bool] = None) -> bool:
  if explicit is not None:
    return explicit
  return os.environ.get("EW_LLM_ADVISORY", "").lower() in ("1", "true", "yes")


def is_critical_decision(verdict: str, outcomes: Optional[dict] = None) -> bool:
  """True when human/LLM review is warranted."""
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
  hs = (outcomes or {}).get("honest_summary") or {}
  structures = {
    tf: (wave_structure.get(tf) or {}).get("structure", "n/a")
    for tf in sorted(wave_structure.keys())
  }
  gaps = executive.get("structural_gaps") or []
  signals = (market_tools or {}).get("confluence_signals") or []

  payload = {
    "symbol": symbol,
    "verdict": executive.get("verdict"),
    "direction": executive.get("direction"),
    "conviction": executive.get("conviction"),
    "playbook": executive.get("playbook"),
    "action": trade_setup.get("action"),
    "entry_zone": trade_setup.get("entry_zone"),
    "stop_loss": trade_setup.get("stop_loss"),
    "take_profit_1": trade_setup.get("take_profit_1"),
    "risk_reward": trade_setup.get("risk_reward"),
    "confidence": trade_setup.get("confidence"),
    "structural_gaps": gaps,
    "ew_structures_by_tf": structures,
    "consensus": {
      "direction": consensus.get("consensus_direction"),
      "agreement_pct": consensus.get("agreement_pct"),
      "engines_valid": consensus.get("engines_valid"),
      "divergences": (consensus.get("divergences") or [])[:3],
    },
    "outcomes": {
      "truth": hs.get("truth"),
      "primary_style": hs.get("primary_style"),
      "full_executable": hs.get("full_executable_count"),
      "probe_executable": hs.get("probe_executable_count"),
    },
    "market_signals": signals[:5],
  }

  return f"""You are a senior risk manager reviewing an algorithmic Elliott Wave trade plan.
Be direct. Flag what the quant model may be missing. Do not be agreeable by default.

TRADE PACKET (JSON):
{json.dumps(payload, indent=2)}

Respond with ONLY valid JSON (no markdown):
{{
  "stance": "agree" | "caution" | "reject",
  "confidence_adjustment": number between -0.15 and 0.15,
  "key_risks": ["risk1", "risk2"],
  "sizing_note": "one sentence on position size",
  "summary": "2-3 sentences max"
}}"""


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


def call_openai_advisory(prompt: str, model: Optional[str] = None) -> dict:
  key = os.environ.get("OPENAI_API_KEY", "").strip()
  if not key:
    return {"available": False, "error": "OPENAI_API_KEY not set"}

  model = model or DEFAULT_OPENAI_MODEL
  try:
    raw = _http_post(
      "https://api.openai.com/v1/chat/completions",
      {
        "Authorization": f"Bearer {key}",
        "Content-Type": "application/json",
      },
      {
        "model": model,
        "temperature": 0.2,
        "response_format": {"type": "json_object"},
        "messages": [
          {"role": "system", "content": "You are a trading risk advisor. Output JSON only."},
          {"role": "user", "content": prompt},
        ],
      },
    )
    content = raw["choices"][0]["message"]["content"]
    parsed = _parse_json_response(content)
    return {"available": True, "model": model, "provider": "openai", **parsed}
  except (urllib.error.URLError, KeyError, json.JSONDecodeError, IndexError) as e:
    return {"available": True, "provider": "openai", "model": model, "error": str(e)}


def call_anthropic_advisory(prompt: str, model: Optional[str] = None) -> dict:
  key = os.environ.get("ANTHROPIC_API_KEY", "").strip()
  if not key:
    return {"available": False, "error": "ANTHROPIC_API_KEY not set"}

  model = model or DEFAULT_ANTHROPIC_MODEL
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
        "max_tokens": 600,
        "temperature": 0.2,
        "system": "You are a trading risk advisor. Respond with JSON only, no markdown.",
        "messages": [{"role": "user", "content": prompt}],
      },
    )
    content = raw["content"][0]["text"]
    parsed = _parse_json_response(content)
    return {"available": True, "model": model, "provider": "anthropic", **parsed}
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
  """
  Consult OpenAI + Anthropic when API keys are present.
  Results are cached per symbol/verdict/price bucket for 1 hour.
  """
  verdict = executive.get("verdict", "")
  price = round(float(trade_setup.get("entry_zone", [0])[0] if trade_setup.get("entry_zone") else 0), 0)
  cache_key = (symbol, verdict, executive.get("direction"), price)

  if use_cache:
    cached = get_cache().get(NAMESPACE, *cache_key)
    if cached is not None:
      cached = dict(cached)
      cached["cache_hit"] = True
      return cached

  prompt = build_advisory_prompt(
    symbol, executive, trade_setup, wave_structure, consensus, outcomes, market_tools
  )

  openai_r = call_openai_advisory(prompt)
  anthropic_r = call_anthropic_advisory(prompt)

  consulted = []
  ok_responses = []
  for label, resp in (("openai", openai_r), ("anthropic", anthropic_r)):
    if resp.get("available") and resp.get("stance"):
      consulted.append(label)
      ok_responses.append(resp)

  result = {
    "critical": True,
    "consulted": consulted,
    "openai": openai_r,
    "anthropic": anthropic_r,
    "consensus_stance": _blend_stances(ok_responses),
    "cache_hit": False,
  }

  summaries = [r.get("summary") for r in ok_responses if r.get("summary")]
  if summaries:
    result["blended_summary"] = " | ".join(summaries)

  adjustments = [r.get("confidence_adjustment") for r in ok_responses if isinstance(r.get("confidence_adjustment"), (int, float))]
  if adjustments:
    result["avg_confidence_adjustment"] = round(sum(adjustments) / len(adjustments), 3)

  if not consulted:
    missing = []
    if not openai_r.get("available"):
      missing.append("openai")
    if not anthropic_r.get("available"):
      missing.append("anthropic")
    result["skipped_reason"] = (
      "No API keys configured (set OPENAI_API_KEY and/or ANTHROPIC_API_KEY)"
      if len(missing) == 2
      else f"Consultation failed for: {', '.join(missing)}"
    )
    print(f"[llm] advisory skipped for {symbol}: {result['skipped_reason']}")
  else:
    print(
      f"[llm] advisory {symbol}: consulted={consulted} "
      f"stance={result['consensus_stance']}"
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
  """Return advisory dict only for critical decisions when enabled."""
  if not enabled:
    return None
  if not is_critical_decision(executive.get("verdict", ""), outcomes):
    return None
  return get_llm_advisory(
    symbol, executive, trade_setup, wave_structure, consensus, outcomes, market_tools
  )
