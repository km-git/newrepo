"""Token savers — tiktoken, EW/GitHub bypass, zstd cache, dedup, session budget."""

from __future__ import annotations

import hashlib
import json
import os
from datetime import date
from typing import Any, Dict, List, Optional, Tuple

from engine.llm_gpt_policy import session_token_limit

# Optional accurate token counting (pip install tiktoken)
try:
  import tiktoken

  _ENC = tiktoken.get_encoding(os.environ.get("EW_TIKTOKEN_ENCODING", "cl100k_base"))

  def estimate_tokens(text: str) -> int:
    return len(_ENC.encode(text or ""))

except ImportError:
  def estimate_tokens(text: str) -> int:
    return max(1, len(text or "") // 4)


def llm_cache_ttl() -> int:
  return int(os.environ.get("EW_LLM_CACHE_TTL", os.environ.get("EW_CACHE_TTL", "14400")))


def ew_bypass_enabled() -> bool:
  """Use GitHub/EW engine consensus instead of LLM when strong (zero tokens)."""
  return os.environ.get("EW_LLM_EW_BYPASS", "1").lower() not in ("0", "false", "no")


def structure_fingerprint(
  symbol: str,
  executive: dict,
  consensus: dict,
  wave_structure: dict,
) -> str:
  """Stable hash of EW state — cache hits across small price moves."""
  structures = {
    tf: (wave_structure.get(tf) or {}).get("structure", "")[:48]
    for tf in sorted(wave_structure.keys())
  }
  payload = {
    "sym": symbol,
    "v": executive.get("verdict"),
    "dir": executive.get("direction"),
    "cons": consensus.get("consensus_direction"),
    "agr": round(float(consensus.get("agreement_pct") or 0), 0),
    "eng": consensus.get("engines_valid"),
    "ew": structures,
    "gaps": tuple((executive.get("structural_gaps") or [])[:3]),
  }
  blob = json.dumps(payload, sort_keys=True, default=str)
  return hashlib.sha256(blob.encode()).hexdigest()[:16]


def ew_consensus_aligns(executive: dict, consensus: dict) -> bool:
  ex_dir = executive.get("direction", "")
  cons_dir = consensus.get("consensus_direction", "")
  if cons_dir in ("BULL", "BEAR") and ex_dir in ("BULL", "BEAR"):
    return ex_dir == cons_dir
  return cons_dir == "NEUTRAL" or ex_dir == cons_dir


def ew_consensus_strong_enough(consensus: dict) -> bool:
  agreement = float(consensus.get("agreement_pct") or 0)
  engines = int(consensus.get("engines_valid") or 0)
  min_agr = float(os.environ.get("EW_LLM_EW_BYPASS_MIN_AGREEMENT", "75"))
  min_eng = int(os.environ.get("EW_LLM_EW_BYPASS_MIN_ENGINES", "2"))
  return agreement >= min_agr and engines >= min_eng


def synthetic_panel_from_ew_consensus(
  executive: dict,
  consensus: dict,
) -> dict:
  """
  Zero-token executive consensus from GitHub EW tools + internal engines.
  Used when agreement is high and direction matches executive draft.
  """
  aligned = ew_consensus_aligns(executive, consensus)
  agreement = float(consensus.get("agreement_pct") or 0)
  engines = consensus.get("engines_valid", 0)
  github = consensus.get("github_tools_used") or []

  if aligned and agreement >= 85:
    stance = "agree"
    adj = 0.03
    summary = f"EW bypass: {agreement:.0f}% agree, {engines} engines, GitHub={len(github)}"
  elif aligned:
    stance = "caution"
    adj = 0.0
    summary = f"EW bypass (moderate): {agreement:.0f}% agree"
  else:
    stance = "caution"
    adj = -0.04
    summary = (
      f"EW bypass: direction split exec={executive.get('direction')} "
      f"vs consensus={consensus.get('consensus_direction')}"
    )

  return {
    "critical": True,
    "consulted": ["ew_github_consensus"],
    "consensus_stance": stance,
    "confidence_adjustment": adj,
    "cache_hit": False,
    "token_budget": {
      "est_input_tokens": 0,
      "est_total_tokens": 0,
      "cache_hit": False,
      "ew_bypass": True,
      "routes": [],
    },
    "intelligence_mode": "ew_bypass",
    "llm_backend": "none",
    "blended_summary": summary,
    "intelligence_panel": {
      "intelligence_mode": "ew_bypass",
      "consensus_stance": stance,
      "confidence_adjustment": adj,
      "escalated_to_premium": False,
      "disagreement": False,
      "disagreement_severity": "none",
      "screen": {
        "openai": {"available": False, "skipped": "ew_bypass"},
        "anthropic": {"available": False, "skipped": "ew_bypass"},
        "routes": [],
      },
      "models_used": {"ew_bypass": True, "github_tools": github},
    },
    "ew_bypass": True,
    "ew_consensus": {
      "agreement_pct": agreement,
      "engines_valid": engines,
      "consensus_direction": consensus.get("consensus_direction"),
      "aligned_with_executive": aligned,
    },
  }


def should_bypass_llm_with_ew(
  executive: dict,
  consensus: dict,
) -> bool:
  if not ew_bypass_enabled():
    return False
  if not ew_consensus_strong_enough(consensus):
    return False
  return True


def compress_prompt_payload(payload: dict) -> str:
  """Minified JSON — no spaces."""
  return json.dumps(payload, separators=(",", ":"), default=str)


class SessionTokenBudget:
  """
  Persistent session token tracker (diskcache + zstd).
  Enforces EW_LLM_MAX_SESSION_TOKENS (default 10,000).
  """

  NAMESPACE = "llm_session_budget"

  def __init__(self) -> None:
    from cache.disk_cache import get_llm_cache

    self._cache = get_llm_cache()
    self._limit = session_token_limit()
    self._key = ("session", date.today().isoformat())

  def _state(self) -> dict:
    return self._cache.get(self.NAMESPACE, *self._key) or {"used": 0, "calls": 0}

  def used(self) -> int:
    return int(self._state().get("used", 0))

  def remaining(self) -> int:
    return max(0, self._limit - self.used())

  def at_limit(self) -> bool:
    return self.remaining() <= 0

  def can_spend(self, estimated: int) -> bool:
    return self.remaining() >= max(0, estimated)

  def record(self, tokens: int) -> int:
    state = self._state()
    state["used"] = int(state.get("used", 0)) + max(0, tokens)
    state["calls"] = int(state.get("calls", 0)) + 1
    self._cache.set(self.NAMESPACE, state, *self._key)
    return state["used"]

  def cap_output(self, prompt: str, requested: int) -> int:
    """Shrink max_output to fit remaining session budget."""
    input_est = estimate_tokens(prompt) + estimate_tokens(
      os.environ.get("EW_LLM_SYSTEM_PROMPT_EST", "120")
    )
    room = self.remaining() - input_est
    if room <= 0:
      return 0
    return max(0, min(requested, room))

  def estimate_call_cost(self, prompt: str, max_output: int) -> int:
    return estimate_tokens(prompt) + max_output

  def summary(self) -> Dict[str, Any]:
    return {
      "limit": self._limit,
      "used": self.used(),
      "remaining": self.remaining(),
      "calls": self._state().get("calls", 0),
      "session_date": self._key[1],
    }


_budget: Optional[SessionTokenBudget] = None


def get_session_budget() -> SessionTokenBudget:
  global _budget
  if _budget is None:
    _budget = SessionTokenBudget()
  return _budget


def usage_from_response(resp: dict, prompt: str, max_output: int) -> int:
  """Extract actual token count from API usage or estimate."""
  usage = resp.get("usage") or {}
  if usage:
    total = usage.get("total_tokens")
    if total is not None:
      return int(total)
    return int(usage.get("prompt_tokens", 0) or 0) + int(usage.get("completion_tokens", 0) or 0)
  if resp.get("stance"):
    return estimate_tokens(prompt) + min(max_output, estimate_tokens(resp.get("summary", "")) + 80)
  return 0


def token_saver_summary() -> Dict[str, Any]:
  budget = get_session_budget()
  return {
    "session_token_limit": session_token_limit(),
    "session_budget": budget.summary(),
    "minimize_gpt_preference": os.environ.get("EW_MINIMIZE_GPT", "0"),
    "ew_bypass": ew_bypass_enabled(),
    "llm_cache_ttl_sec": llm_cache_ttl(),
    "tiktoken": _tiktoken_available(),
    "libraries": ["tiktoken", "diskcache", "zstandard", "cache/dedup", "cache/TokenStore"],
    "rules": [
      f"EW_LLM_MAX_SESSION_TOKENS={session_token_limit()} — hard session cap",
      "EW_LLM_EW_BYPASS=1 — skip LLM when GitHub EW consensus ≥75% + 2 engines",
      "EW_LLM_CACHE_TTL — structure-keyed zstd disk cache (default 4h)",
      "tiktoken — accurate pre-call estimates",
      "zstd + diskcache — compressed advisory blobs with dedup keys",
      "TokenStore — pipeline logs store hashes not full payloads",
      "compact JSON prompts — ~60% fewer input tokens",
      "per-task output caps — workhorse 120, screen 150",
      "EW_MINIMIZE_GPT=0 (default) — GPT allowed, budget-limited not blocked",
    ],
  }


def _tiktoken_available() -> bool:
  try:
    import tiktoken  # noqa: F401
    return True
  except ImportError:
    return False
