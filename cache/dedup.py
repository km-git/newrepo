"""Deduplication utilities for harmonic patterns, monowaves, and tool-call logs."""

from __future__ import annotations

import hashlib
import json
from typing import Any, Iterable, List, Sequence


def _fingerprint(obj: Any) -> str:
  return hashlib.sha256(
    json.dumps(obj, sort_keys=True, default=str).encode()
  ).hexdigest()[:16]


def dedup_harmonics(patterns: Sequence[dict]) -> List[dict]:
  """Remove duplicate harmonic overlaps by (tf, pattern, prz_low, prz_high)."""
  seen: set[str] = set()
  out: List[dict] = []
  for p in patterns:
    key = _fingerprint(
      (p.get("tf"), p.get("pattern"), round(p.get("prz_low", 0), 2), round(p.get("prz_high", 0), 2))
    )
    if key not in seen:
      seen.add(key)
      out.append(p)
  return out


def dedup_monowaves(mws: Sequence[dict], price_tol: float = 0.01) -> List[dict]:
  """Collapse adjacent monowaves with identical endpoints within tolerance."""
  if not mws:
    return []
  out = [mws[0]]
  for m in mws[1:]:
    prev = out[-1]
    same_type = prev["type"] == m["type"]
    same_end = abs(prev["price_end"] - m["price_end"]) <= price_tol
    if same_type and same_end:
      out[-1] = {**prev, "idx_end": m["idx_end"], "date_end": m["date_end"]}
    else:
      out.append(m)
  return out


def dedup_tool_calls(log: Iterable[dict]) -> List[dict]:
  """Keep first occurrence per (tool, args) pair — saves tokens in agent context."""
  seen: set[tuple[str, str]] = set()
  out: List[dict] = []
  for entry in log:
    pair = (entry.get("tool", ""), entry.get("args", ""))
    if pair not in seen:
      seen.add(pair)
      out.append(entry)
  return out
