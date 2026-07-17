"""Compact GitHub context for architect decisions — cached, token-efficient."""

from __future__ import annotations

import os
from typing import Any, Dict, List, Optional

from cache.disk_cache import get_cache
from engine.architect_budget import compact_json, count_tokens, trim_context

GITHUB_CACHE_NS = "github_context_v1"
DEFAULT_MAX_TOKENS = 1500


def _parse_repo(repo: str) -> tuple[str, str]:
  repo = repo.strip().rstrip("/")
  if "github.com/" in repo:
    parts = repo.split("github.com/")[-1].split("/")
    return parts[0], parts[1]
  if "/" in repo:
    o, n = repo.split("/", 1)
    return o, n.replace(".git", "")
  raise ValueError(f"Invalid repo: {repo}")


def fetch_github_summary(
  repo: str,
  *,
  max_prs: int = 3,
  max_issues: int = 3,
  token: Optional[str] = None,
  max_tokens: int = DEFAULT_MAX_TOKENS,
  use_cache: bool = True,
) -> Dict[str, Any]:
  """
  Fetch compact PR + issue summary for architect context.
  Uses PyGithub. Cached via diskcache.
  """
  owner, name = _parse_repo(repo)
  cache = get_cache()
  cache_key = (owner, name, max_prs, max_issues)

  if use_cache:
    hit = cache.get(GITHUB_CACHE_NS, *cache_key)
    if hit is not None:
      return {**hit, "cache_hit": True}

  token = token or os.environ.get("GITHUB_TOKEN", os.environ.get("GH_TOKEN", "")).strip()
  if not token:
    return {
      "repo": f"{owner}/{name}",
      "error": "no GITHUB_TOKEN",
      "open_prs": [],
      "open_issues": [],
      "cache_hit": False,
    }

  try:
    from github import Github

    gh = Github(token)
    r = gh.get_repo(f"{owner}/{name}")
    prs: List[dict] = []
    for pr in r.get_pulls(state="open")[:max_prs]:
      prs.append({
        "n": pr.number,
        "title": (pr.title or "")[:80],
        "branch": pr.head.ref,
        "user": pr.user.login if pr.user else "?",
      })
    issues: List[dict] = []
    for issue in r.get_issues(state="open")[: max_issues + max_prs]:
      if issue.pull_request:
        continue
      issues.append({
        "n": issue.number,
        "title": (issue.title or "")[:80],
        "labels": [l.name for l in issue.labels[:3]],
      })
      if len(issues) >= max_issues:
        break

    summary = {
      "repo": f"{owner}/{name}",
      "default_branch": r.default_branch,
      "open_prs": prs,
      "open_issues": issues,
      "stars": r.stargazers_count,
      "cache_hit": False,
    }
    cache.set(GITHUB_CACHE_NS, summary, *cache_key)
    return _fit_token_budget(summary, max_tokens)
  except Exception as exc:
    return {
      "repo": f"{owner}/{name}",
      "error": str(exc)[:120],
      "open_prs": [],
      "open_issues": [],
      "cache_hit": False,
    }


def _fit_token_budget(summary: dict, max_tokens: int) -> dict:
  blob = compact_json(summary)
  if count_tokens(blob) <= max_tokens:
    return summary
  trimmed, _ = trim_context(blob, max_tokens)
  return {"compact": trimmed, "truncated": True, **{k: summary[k] for k in ("repo", "cache_hit")}}


def github_context_for_architect(repo: str, max_tokens: int = 1500) -> str:
  """One-liner for architect prompt CTX field."""
  s = fetch_github_summary(repo, max_tokens=max_tokens)
  return compact_json(s)
