"""LLM backend selection — Cursor Pro (default) vs direct API."""

from __future__ import annotations

import os
from typing import Literal

Backend = Literal["cursor", "direct"]


def cursor_available() -> bool:
  return bool(os.environ.get("CURSOR_API_KEY", "").strip())


def llm_backend() -> Backend:
  """
  EW_LLM_BACKEND:
  - cursor (default when CURSOR_API_KEY is set): Pro plan models via Cloud Agents API
  - direct: OPENAI_API_KEY / ANTHROPIC_API_KEY HTTP calls
  """
  forced = os.environ.get("EW_LLM_BACKEND", "").lower().strip()
  if forced in ("cursor", "direct"):
    return forced  # type: ignore[return-value]
  if cursor_available():
    return "cursor"
  return "direct"


def advisory_credentials_available() -> bool:
  if llm_backend() == "cursor":
    return cursor_available()
  return bool(
    os.environ.get("OPENAI_API_KEY", "").strip()
    or os.environ.get("ANTHROPIC_API_KEY", "").strip()
  )


def credentials_hint() -> str:
  if llm_backend() == "cursor":
    return "CURSOR_API_KEY (from cursor.com/dashboard → API Keys)"
  return "OPENAI_API_KEY or ANTHROPIC_API_KEY"
