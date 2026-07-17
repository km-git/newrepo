"""Cursor Cloud Agents API — advisory via Pro plan models (no direct OpenAI/Anthropic keys)."""

from __future__ import annotations

import base64
import json
import os
import time
import urllib.error
import urllib.request
from typing import Any, Dict, List, Optional, Tuple

from engine.llm_token_router import DEFAULT_MAX_OUTPUT_TOKENS, SYSTEM_PROMPT

CURSOR_API_BASE = os.environ.get("EW_CURSOR_API_BASE", "https://api.cursor.com").rstrip("/")

# Cursor model IDs — cheap screen vs premium tiebreaker (override via env)
CURSOR_CHEAP_OPENAI = os.environ.get("EW_CURSOR_CHEAP_OPENAI", "gpt-5-mini")
CURSOR_CHEAP_ANTHROPIC = os.environ.get("EW_CURSOR_CHEAP_ANTHROPIC", "composer-2.5")
CURSOR_PREMIUM_OPENAI = os.environ.get("EW_CURSOR_PREMIUM_OPENAI", "gpt-5.2")
CURSOR_PREMIUM_ANTHROPIC = os.environ.get("EW_CURSOR_PREMIUM_ANTHROPIC", "claude-4.5-sonnet")

TERMINAL_RUN_STATUSES = frozenset({"FINISHED", "ERROR", "CANCELLED", "EXPIRED"})


def cursor_api_key() -> str:
  return os.environ.get("CURSOR_API_KEY", "").strip()


def cursor_available() -> bool:
  return bool(cursor_api_key())


def cursor_model_for(provider: str, tier: str = "cheap") -> str:
  """Map logical provider slot → Cursor model id."""
  if tier == "standard":
    return CURSOR_PREMIUM_OPENAI if provider == "openai" else CURSOR_PREMIUM_ANTHROPIC
  return CURSOR_CHEAP_OPENAI if provider == "openai" else CURSOR_CHEAP_ANTHROPIC


def _auth_header() -> dict:
  key = cursor_api_key()
  token = base64.b64encode(f"{key}:".encode()).decode()
  return {"Authorization": f"Basic {token}", "Content-Type": "application/json"}


def _http(method: str, path: str, body: Optional[dict] = None, timeout: int = 60) -> dict:
  url = f"{CURSOR_API_BASE}{path}"
  data = json.dumps(body).encode() if body is not None else None
  req = urllib.request.Request(url, data=data, headers=_auth_header(), method=method)
  with urllib.request.urlopen(req, timeout=timeout) as resp:
    return json.loads(resp.read().decode())


def _parse_json_response(text: str) -> dict:
  text = (text or "").strip()
  if text.startswith("```"):
    text = text.split("```", 2)[1]
    if text.startswith("json"):
      text = text[4:]
  return json.loads(text.strip())


def _build_cursor_prompt(prompt: str) -> str:
  user = prompt.split("\n\nDATA:", 1)[-1] if "DATA:" in prompt else prompt
  return (
    f"{SYSTEM_PROMPT}\n"
    "Reply with a single JSON object only. No markdown fences. No tools. No prose.\n\n"
    f"{user}\n\nJSON:"
  )


def _poll_run(agent_id: str, run_id: str) -> dict:
  timeout_s = int(os.environ.get("EW_CURSOR_POLL_TIMEOUT", "120"))
  interval = float(os.environ.get("EW_CURSOR_POLL_INTERVAL", "1.0"))
  deadline = time.time() + timeout_s
  last: dict = {}
  while time.time() < deadline:
    last = _http("GET", f"/v1/agents/{agent_id}/runs/{run_id}")
    status = last.get("status", "")
    if status in TERMINAL_RUN_STATUSES:
      return last
    time.sleep(interval)
  raise TimeoutError(f"Cursor run {run_id} timed out after {timeout_s}s (last={last.get('status')})")


def _archive_agent(agent_id: str) -> None:
  try:
    _http("POST", f"/v1/agents/{agent_id}/archive")
  except (urllib.error.URLError, OSError, KeyError):
    pass


def call_cursor_advisory(prompt: str, model_id: str, provider: str = "cursor") -> dict:
  """
  One-shot no-repo cloud agent run for compact advisory JSON.
  Bills against Cursor Pro pools (model-dependent).
  """
  if not cursor_available():
    return {"available": False, "error": "CURSOR_API_KEY not set"}

  full_prompt = _build_cursor_prompt(prompt)
  agent_id = None
  try:
    created = _http(
      "POST",
      "/v1/agents",
      {
        "prompt": {"text": full_prompt},
        "model": {"id": model_id},
        "name": f"ew-advisory-{model_id}"[:100],
      },
      timeout=90,
    )
    agent = created.get("agent") or {}
    run = created.get("run") or {}
    agent_id = agent.get("id")
    run_id = run.get("id")
    if not agent_id or not run_id:
      return {
        "available": True,
        "provider": provider,
        "model": model_id,
        "backend": "cursor",
        "error": f"unexpected create response: {created!r}",
      }

    finished = _poll_run(agent_id, run_id)
    status = finished.get("status")
    if status != "FINISHED":
      return {
        "available": True,
        "provider": provider,
        "model": model_id,
        "backend": "cursor",
        "error": f"run {status}: {finished.get('result', '')[:200]}",
      }

    raw = finished.get("result") or ""
    parsed = _parse_json_response(raw)
    return {
      "available": True,
      "model": model_id,
      "provider": provider,
      "backend": "cursor",
      "duration_ms": finished.get("durationMs"),
      **parsed,
    }
  except (urllib.error.URLError, TimeoutError, json.JSONDecodeError, KeyError, IndexError) as e:
    return {
      "available": True,
      "provider": provider,
      "model": model_id,
      "backend": "cursor",
      "error": str(e),
    }
  finally:
    if agent_id:
      _archive_agent(agent_id)


def call_cursor_provider_advisory(provider: str, model: str, tier: str, prompt: str) -> dict:
  """Panel hook — provider slot maps to Cursor model id."""
  model_id = model if model and not model.startswith("gpt-4o") else cursor_model_for(provider, tier)
  return call_cursor_advisory(prompt, model_id, provider=provider)


def list_cursor_models() -> List[dict]:
  """GET /v1/models — models available on the account."""
  if not cursor_available():
    return []
  try:
    raw = _http("GET", "/v1/models")
    return raw.get("models") or raw.get("items") or []
  except (urllib.error.URLError, KeyError, json.JSONDecodeError):
    return []
