"""Token-efficient LLM routing — cheap models by default, compact prompts, provider selection."""

from __future__ import annotations

import json
import os
from typing import Any, Dict, List, Literal, Optional, Tuple

Provider = Literal["openai", "anthropic"]

# Cheapest capable models (Jul 2026 menu — override via env)
CHEAP_OPENAI = "gpt-4o-mini"
STANDARD_OPENAI = "gpt-4o"
CHEAP_ANTHROPIC = "claude-3-5-haiku-20241022"
STANDARD_ANTHROPIC = "claude-sonnet-4-20250514"

# Output cap — advisory JSON is ~150 tokens
DEFAULT_MAX_OUTPUT_TOKENS = int(os.environ.get("EW_LLM_MAX_OUTPUT", "280"))

SYSTEM_PROMPT = "Risk advisor. JSON only: stance(agree|caution|reject), confidence_adjustment, key_risks[], sizing_note, summary."


def estimate_tokens(text: str) -> int:
  """Rough token estimate (chars/4) — good enough for budget logging."""
  return max(1, len(text) // 4)


def provider_mode() -> str:
  return os.environ.get("EW_LLM_PROVIDER", "auto").lower().strip()


def tier_for_verdict(verdict: str, conviction: str = "") -> str:
  """
  cheap: mini/haiku — default for CONDITIONAL_GO and batch
  standard: sonnet/gpt-4o — only for GO with high conviction or EW_LLM_TIER=standard
  """
  forced = os.environ.get("EW_LLM_TIER", "").lower().strip()
  if forced in ("cheap", "standard"):
    return forced
  if verdict == "GO" and conviction == "high":
    return "standard" if os.environ.get("EW_LLM_PREMIUM_GO", "").lower() in ("1", "true") else "cheap"
  return "cheap"


def model_for(provider: Provider, tier: str = "cheap") -> str:
  if provider == "openai":
    default = CHEAP_OPENAI if tier == "cheap" else STANDARD_OPENAI
    return os.environ.get("EW_OPENAI_MODEL", default)
  default = CHEAP_ANTHROPIC if tier == "cheap" else STANDARD_ANTHROPIC
  return os.environ.get("EW_ANTHROPIC_MODEL", default)


def select_providers() -> List[Provider]:
  """
  Provider selection (token budget):
  - cursor backend: virtual openai+anthropic slots (routed via Cursor Cloud Agents API)
  - auto (direct): ONE provider — OpenAI if key present, else Anthropic
  - dual: both direct keys (2× cost)
  """
  from engine.llm_backend import cursor_available, llm_backend

  if llm_backend() == "cursor":
    return ["openai", "anthropic"] if cursor_available() else []

  mode = provider_mode()
  has_openai = bool(os.environ.get("OPENAI_API_KEY", "").strip())
  has_anthropic = bool(os.environ.get("ANTHROPIC_API_KEY", "").strip())

  if mode == "dual":
    return [p for p in ("openai", "anthropic") if (p == "openai" and has_openai) or (p == "anthropic" and has_anthropic)]
  if mode == "openai":
    return ["openai"] if has_openai else []
  if mode == "anthropic":
    return ["anthropic"] if has_anthropic else []
  # auto — single cheapest path
  if has_openai:
    return ["openai"]
  if has_anthropic:
    return ["anthropic"]
  return []


def compact_advisory_payload(
  symbol: str,
  executive: dict,
  trade_setup: dict,
  wave_structure: dict,
  consensus: dict,
  outcomes: dict,
  market_tools: Optional[dict] = None,
  brain_lessons: Optional[List[str]] = None,
) -> dict:
  """Minified trade packet — short keys, no prose, no indent."""
  hs = (outcomes or {}).get("honest_summary") or {}
  structures = {
    tf: (wave_structure.get(tf) or {}).get("structure", "?")[:40]
    for tf in sorted(wave_structure.keys())
  }
  payload = {
    "sym": symbol,
    "v": executive.get("verdict"),
    "dir": executive.get("direction"),
    "conv": executive.get("conviction"),
    "act": trade_setup.get("action"),
    "ez": trade_setup.get("entry_zone"),
    "sl": trade_setup.get("stop_loss"),
    "tp": trade_setup.get("take_profit_1"),
    "rr": trade_setup.get("risk_reward"),
    "conf": trade_setup.get("confidence"),
    "gaps": (executive.get("structural_gaps") or [])[:4],
    "ew": structures,
    "cons": consensus.get("consensus_direction"),
    "agr": consensus.get("agreement_pct"),
    "eng": consensus.get("engines_valid"),
    "out": hs.get("truth", "")[:120],
    "exe": hs.get("full_executable_count", 0),
    "prb": hs.get("probe_executable_count", 0),
    "sig": ((market_tools or {}).get("confluence_signals") or [])[:3],
  }
  if brain_lessons:
    payload["brain"] = brain_lessons[:5]
  return payload


def build_compact_prompt(payload: dict) -> str:
  """Single-line JSON user message — minimizes input tokens vs indented block."""
  blob = json.dumps(payload, separators=(",", ":"), default=str)
  return f"{SYSTEM_PROMPT}\n\nDATA:{blob}\n\nJSON:"


def routing_plan(verdict: str, conviction: str = "") -> List[Tuple[Provider, str, str]]:
  """Returns [(provider, model, tier), ...] for this decision."""
  tier = tier_for_verdict(verdict, conviction)
  return [(p, model_for(p, tier), tier) for p in select_providers()]


def token_budget_report(prompt: str, routes: List[Tuple[Provider, str, str]], cache_hit: bool = False) -> dict:
  est_in = estimate_tokens(prompt)
  return {
    "prompt_chars": len(prompt),
    "est_input_tokens": est_in,
    "max_output_tokens": DEFAULT_MAX_OUTPUT_TOKENS,
    "est_total_tokens": est_in + DEFAULT_MAX_OUTPUT_TOKENS * max(len(routes), 1),
    "provider_mode": provider_mode(),
    "routes": [{"provider": p, "model": m, "tier": t} for p, m, t in routes],
    "cache_hit": cache_hit,
  }
