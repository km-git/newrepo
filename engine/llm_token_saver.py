"""Token savers — per-model budget, tiktoken, EW bypass, zstd cache, library registry."""

from __future__ import annotations

import hashlib
import json
import os
from datetime import date
from typing import Any, Dict, List, Optional, Tuple

from engine.llm_gpt_policy import per_model_token_limit

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


class PerModelTokenBudget:
  """
  Per-model token tracker (diskcache + zstd).
  Each model gets EW_LLM_MAX_TOKENS_PER_MODEL (default 10,000) — independent caps.
  """

  NAMESPACE = "llm_model_budget"

  def __init__(self) -> None:
    from cache.disk_cache import get_llm_cache

    self._cache = get_llm_cache()
    self._limit = per_model_token_limit()
    self._key = ("per_model", date.today().isoformat())

  def _all_models(self) -> dict:
    return self._cache.get(self.NAMESPACE, *self._key) or {}

  def _model_entry(self, model: str) -> dict:
    return dict(self._all_models().get(model, {"used": 0, "calls": 0}))

  def used(self, model: str) -> int:
    return int(self._model_entry(model).get("used", 0))

  def remaining(self, model: str) -> int:
    return max(0, self._limit - self.used(model))

  def at_limit(self, model: str) -> bool:
    return self.remaining(model) <= 0

  def can_spend(self, model: str, estimated: int) -> bool:
    return self.remaining(model) >= max(0, estimated)

  def record(self, model: str, tokens: int) -> int:
    state = self._all_models()
    entry = self._model_entry(model)
    entry["used"] = int(entry.get("used", 0)) + max(0, tokens)
    entry["calls"] = int(entry.get("calls", 0)) + 1
    state[model] = entry
    self._cache.set(self.NAMESPACE, state, *self._key)
    return entry["used"]

  def cap_output(self, model: str, prompt: str, requested: int) -> int:
    """Shrink max_output to fit this model's remaining budget."""
    input_est = estimate_tokens(prompt) + estimate_tokens(
      os.environ.get("EW_LLM_SYSTEM_PROMPT_EST", "120")
    )
    room = self.remaining(model) - input_est
    if room <= 0:
      return 0
    return max(0, min(requested, room))

  def model_summary(self, model: str) -> Dict[str, Any]:
    entry = self._model_entry(model)
    used = int(entry.get("used", 0))
    return {
      "model": model,
      "limit": self._limit,
      "used": used,
      "remaining": max(0, self._limit - used),
      "calls": int(entry.get("calls", 0)),
    }

  def summary(self) -> Dict[str, Any]:
    state = self._all_models()
    models = {
      m: {
        "limit": self._limit,
        "used": int(e.get("used", 0)),
        "remaining": max(0, self._limit - int(e.get("used", 0))),
        "calls": int(e.get("calls", 0)),
      }
      for m, e in state.items()
    }
    return {
      "per_model_limit": self._limit,
      "models": models,
      "session_date": self._key[1],
    }


# Backward-compat alias
SessionTokenBudget = PerModelTokenBudget

_budget: Optional[PerModelTokenBudget] = None


def get_model_budget() -> PerModelTokenBudget:
  global _budget
  if _budget is None:
    _budget = PerModelTokenBudget()
  return _budget


def get_session_budget() -> PerModelTokenBudget:
  """Backward-compat — now tracks per-model limits."""
  return get_model_budget()


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
  from engine.token_saver_registry import registry_summary

  budget = get_model_budget()
  reg = registry_summary()
  return {
    "per_model_token_limit": per_model_token_limit(),
    "model_budgets": budget.summary(),
    "minimize_gpt_preference": os.environ.get("EW_MINIMIZE_GPT", "0"),
    "ew_bypass": ew_bypass_enabled(),
    "llm_cache_ttl_sec": llm_cache_ttl(),
    "tiktoken": _tiktoken_available(),
    "registry": reg,
    "rules": [
      f"EW_LLM_MAX_TOKENS_PER_MODEL={per_model_token_limit()} — each model capped independently",
      "EW_LLM_EW_BYPASS=1 — skip LLM when GitHub EW consensus ≥75% + 2 engines",
      "EW_LLM_CACHE_TTL — structure-keyed zstd disk cache (default 4h)",
      "tiktoken + llm-token-optimizer + tokenpruner — prompt compression",
      "diskcache + zstandard + cachetic — compressed persistent cache",
      "joblib memoize — deduplicate repeated LLM calls",
      "TokenStore + dedup — pipeline logs store hashes not payloads",
      "EW_MINIMIZE_GPT=0 (default) — GPT allowed, per-model budget-limited",
    ],
  }


def _tiktoken_available() -> bool:
  try:
    import tiktoken  # noqa: F401
    return True
  except ImportError:
    return False
