"""Token-saving result store: hash payloads instead of embedding full results in logs."""

from __future__ import annotations

import hashlib
import json
from typing import Any, Dict, List, Optional

from cache.disk_cache import get_cache


def result_hash(payload: Any) -> str:
  """SHA-256 digest of canonical JSON — used in tool_calls_log.result_hash."""
  canonical = json.dumps(payload, sort_keys=True, default=str)
  return hashlib.sha256(canonical.encode()).hexdigest()


def compact_summary(payload: Any, max_keys: int = 8) -> Dict[str, Any]:
  """Truncate nested dicts for agent-facing summaries (token saving)."""
  if not isinstance(payload, dict):
    return {"value": str(payload)[:200]}
  out: Dict[str, Any] = {}
  for i, (k, v) in enumerate(payload.items()):
    if i >= max_keys:
      out["_truncated"] = len(payload) - max_keys
      break
    if isinstance(v, (list, dict)) and len(str(v)) > 120:
      out[k] = f"<{type(v).__name__} len={len(v)} hash={result_hash(v)[:12]}>"
    else:
      out[k] = v
  return out


class TokenStore:
  """Store full pipeline stage results by hash; logs only carry hashes."""

  NAMESPACE = "tool_results"

  def __init__(self):
    self._cache = get_cache()

  def store(self, tool: str, args: dict, result: Any) -> str:
    h = result_hash({"tool": tool, "args": args, "result": result})
    self._cache.set(self.NAMESPACE, result, h)
    return h

  def retrieve(self, h: str) -> Optional[Any]:
    return self._cache.get(self.NAMESPACE, h)

  def log_entry(self, tool: str, args: dict, result: Any) -> dict:
    h = self.store(tool, args, result)
    return {
      "tool": tool,
      "args": json.dumps(args, default=str),
      "result_hash": h,
    }


def build_tool_calls_log(stages: List[tuple[str, dict, Any]]) -> List[dict]:
  store = TokenStore()
  return [store.log_entry(tool, args, result) for tool, args, result in stages]
