"""Cursor Cloud Agents API — task-aware routing via Cursor Pro pools."""

from __future__ import annotations

import base64
import json
import os
import time
import urllib.error
import urllib.request
from typing import Any, Dict, List, Optional

from engine.llm_task_router import TaskKind, max_output_for_task, resolve_model
from engine.llm_token_router import SYSTEM_PROMPT

CURSOR_API_BASE = os.environ.get("EW_CURSOR_API_BASE", "https://api.cursor.com").rstrip("/")

TERMINAL_RUN_STATUSES = frozenset({"FINISHED", "ERROR", "CANCELLED", "EXPIRED"})


def cursor_api_key() -> str:
  return os.environ.get("CURSOR_API_KEY", "").strip()


def cursor_available() -> bool:
  from engine.llm_backend import cursor_available as _avail

  return _avail()


def cursor_model_for(provider: str, tier: str = "cheap") -> str:
  """Backward-compat shim — prefer resolve_model(task=...)."""
  from engine.llm_task_router import TaskKind

  task: TaskKind = "screen" if tier == "cheap" else "executive"
  model, _, _ = resolve_model(provider, task)  # type: ignore[arg-type]
  return model


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


def _build_cursor_prompt(prompt: str, task: TaskKind) -> str:
  user = prompt.split("\n\nDATA:", 1)[-1] if "DATA:" in prompt else prompt
  if task in ("architect", "synthesis", "planning"):
    header = f"{SYSTEM_PROMPT}\nTask: {task}. Be thorough but concise.\n"
  else:
    header = f"{SYSTEM_PROMPT}\nReply with a single JSON object only. No markdown. No tools.\n"
  return f"{header}{user}\n\nJSON:"


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


def call_cursor_advisory(
  prompt: str,
  model_id: str,
  provider: str = "cursor",
  *,
  task: TaskKind = "screen",
  max_output: Optional[int] = None,
) -> dict:
  """One-shot no-repo cloud agent run — task sets token budget and prompt shape."""
  if not cursor_available():
    return {"available": False, "error": "CURSOR_API_KEY not set"}

  max_out = max_output or max_output_for_task(task)
  full_prompt = _build_cursor_prompt(prompt, task)
  agent_id = None
  try:
    created = _http(
      "POST",
      "/v1/agents",
      {
        "prompt": {"text": full_prompt},
        "model": {"id": model_id},
        "name": f"ew-{task}-{model_id}"[:100],
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
        "task": task,
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
        "task": task,
        "error": f"run {status}: {finished.get('result', '')[:200]}",
      }

    raw = finished.get("result") or ""
    parsed = _parse_json_response(raw) if task not in ("architect", "synthesis") else {"summary": raw[:2000]}
    return {
      "available": True,
      "model": model_id,
      "provider": provider,
      "backend": "cursor",
      "task": task,
      "max_output": max_out,
      "duration_ms": finished.get("durationMs"),
      **parsed,
    }
  except (urllib.error.URLError, TimeoutError, json.JSONDecodeError, KeyError, IndexError) as e:
    return {
      "available": True,
      "provider": provider,
      "model": model_id,
      "backend": "cursor",
      "task": task,
      "error": str(e),
    }
  finally:
    if agent_id:
      _archive_agent(agent_id)


def call_cursor_provider_advisory(
  provider: str,
  model: str,
  tier: str,
  prompt: str,
  *,
  task: TaskKind = "screen",
  max_output: Optional[int] = None,
) -> dict:
  model_id, _tier, max_out = resolve_model(provider, task)  # type: ignore[arg-type]
  if model and not model.startswith("gpt-4o"):
    model_id = model
  return call_cursor_advisory(
    prompt,
    model_id,
    provider=provider,
    task=task,
    max_output=max_output or max_out,
  )


def list_cursor_models() -> List[dict]:
  if not cursor_available():
    return []
  try:
    raw = _http("GET", "/v1/models")
    return raw.get("models") or raw.get("items") or []
  except (urllib.error.URLError, KeyError, json.JSONDecodeError):
    return []
