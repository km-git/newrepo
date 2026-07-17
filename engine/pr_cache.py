"""PR review cache — skip re-review when head SHA unchanged."""

from __future__ import annotations

import hashlib
import json
from typing import Any, Dict, Optional

from cache.disk_cache import get_llm_cache

NAMESPACE = "pr_executive_review"


def pr_cache_key(pr_number: int, repo: str, head_sha: str) -> str:
  payload = json.dumps({"pr": pr_number, "repo": repo, "head": head_sha}, sort_keys=True)
  return hashlib.sha256(payload.encode()).hexdigest()[:20]


def get_cached_review(pr_number: int, repo: str, head_sha: str) -> Optional[Dict[str, Any]]:
  if not head_sha:
    return None
  return get_llm_cache().get(NAMESPACE, pr_cache_key(pr_number, repo, head_sha))


def set_cached_review(pr_number: int, repo: str, head_sha: str, result: Dict[str, Any]) -> None:
  if not head_sha:
    return
  get_llm_cache().set(NAMESPACE, result, pr_cache_key(pr_number, repo, head_sha))
