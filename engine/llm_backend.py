"""LLM backend selection — Cursor Pro (default) vs direct OpenAI/Anthropic API."""

from __future__ import annotations

import os
from pathlib import Path
from typing import Literal

Backend = Literal["cursor", "direct"]

_ROOT = Path(__file__).resolve().parent.parent
_BOOTSTRAPPED = False

# Alternate env names users / CI may set for the same Cursor Cloud Agents key.
_CURSOR_KEY_NAMES = (
  "CURSOR_API_KEY",
  "CURSOR_AGENT_API_KEY",
  "CURSOR_CLOUD_AGENT_API_KEY",
)


def _load_env_file() -> None:
  """Load repo `.env` without overwriting variables already in the environment."""
  env_path = _ROOT / ".env"
  if not env_path.is_file():
    return
  try:
    for line in env_path.read_text(encoding="utf-8").splitlines():
      line = line.strip()
      if not line or line.startswith("#") or "=" not in line:
        continue
      key, _, value = line.partition("=")
      key = key.strip()
      value = value.strip().strip("'\"")
      if key and key not in os.environ:
        os.environ[key] = value
  except OSError:
    pass


def bootstrap_llm_env() -> dict:
  """
  One-time LLM env bootstrap:
  - load `.env`
  - default EW_LLM_BACKEND=cursor (Cursor Pro pools, not direct OAI/Anthropic HTTP)
  """
  global _BOOTSTRAPPED
  if _BOOTSTRAPPED:
    return {"bootstrapped": True, "backend": llm_backend(), "cursor_key": cursor_available()}
  _load_env_file()
  if not os.environ.get("EW_LLM_BACKEND", "").strip():
    os.environ["EW_LLM_BACKEND"] = "cursor"
  _BOOTSTRAPPED = True
  return {
    "bootstrapped": True,
    "backend": llm_backend(),
    "cursor_key": cursor_available(),
    "cursor_key_source": cursor_key_source(),
  }


def _ensure_bootstrapped() -> None:
  if not _BOOTSTRAPPED:
    bootstrap_llm_env()


def cursor_api_key() -> str:
  _ensure_bootstrapped()
  for name in _CURSOR_KEY_NAMES:
    value = os.environ.get(name, "").strip()
    if value:
      return value
  return ""


def cursor_key_source() -> str:
  _ensure_bootstrapped()
  for name in _CURSOR_KEY_NAMES:
    if os.environ.get(name, "").strip():
      return name
  return ""


def cursor_available() -> bool:
  return bool(cursor_api_key())


def llm_backend() -> Backend:
  """
  EW_LLM_BACKEND:
  - cursor (default): Pro plan models via Cursor Cloud Agents API — set CURSOR_API_KEY
  - direct: OPENAI_API_KEY / ANTHROPIC_API_KEY HTTP calls (opt-in only)
  """
  _ensure_bootstrapped()
  forced = os.environ.get("EW_LLM_BACKEND", "").lower().strip()
  if forced in ("cursor", "direct"):
    return forced  # type: ignore[return-value]
  return "cursor"


def advisory_credentials_available() -> bool:
  if llm_backend() == "cursor":
    return cursor_available()
  return bool(
    os.environ.get("OPENAI_API_KEY", "").strip()
    or os.environ.get("ANTHROPIC_API_KEY", "").strip()
  )


def credentials_hint() -> str:
  if llm_backend() == "cursor":
    return "CURSOR_API_KEY (cursor.com/dashboard → API Keys)"
  return "OPENAI_API_KEY or ANTHROPIC_API_KEY (or set EW_LLM_BACKEND=cursor + CURSOR_API_KEY)"
