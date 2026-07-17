"""Policy — per-model token limits (default 10k each); GPT allowed but budgeted."""

from __future__ import annotations

import os


def per_model_token_limit() -> int:
  """Hard cap per model — default 10,000 tokens each (not shared across models)."""
  return int(
    os.environ.get(
      "EW_LLM_MAX_TOKENS_PER_MODEL",
      os.environ.get("EW_LLM_MAX_SESSION_TOKENS", "10000"),
    )
  )


def session_token_limit() -> int:
  """Backward-compat alias — now means per-model limit."""
  return per_model_token_limit()


def minimize_gpt_enabled() -> bool:
  """
  Optional preference for first-party models over GPT API.
  Default off — GPT is allowed; per-model budget enforces the limit.
  """
  return os.environ.get("EW_MINIMIZE_GPT", "0").lower() in ("1", "true", "yes")


def gpt_free_screen_slot_b() -> str:
  """Second screen slot when EW_MINIMIZE_GPT=1."""
  return os.environ.get("EW_MODEL_SCREEN_B_NO_GPT", "composer-2.5")


def gpt_replacement_for(model_key: str, default: str) -> str:
  """
  Map roster MODEL keys to first-party alternatives when EW_MINIMIZE_GPT=1.
  When off (default), returns the GPT/default model unchanged.
  """
  if not minimize_gpt_enabled():
    return default

  replacements = {
    "screen_b": gpt_free_screen_slot_b(),
    "workhorse_api": os.environ.get("EW_MODEL_WORKHORSE_FP", "composer-2.5"),
    "nano": os.environ.get("EW_MODEL_WORKHORSE_FP", "composer-2.5"),
    "mild_tb": os.environ.get("EW_MODEL_GROK_HIGH", "cursor-grok-4.5-high"),
    "light_plan": os.environ.get("EW_MODEL_GROK_HIGH", "cursor-grok-4.5-high"),
    "sol": os.environ.get("EW_MODEL_OPUS", "claude-opus-4-8"),
  }
  return replacements.get(model_key, default)


def is_gpt_model(model_id: str) -> bool:
  m = (model_id or "").lower()
  return m.startswith("gpt-") or ("openai" in m and "grok" not in m)
