"""Detect and close PRs superseded by code already on main."""

from __future__ import annotations

import os
import subprocess
from pathlib import Path
from typing import Any, Dict, List, Optional, Set

from engine.pr_github import close_pr, ensure_gh_auth, fetch_pr_context, list_open_prs

# Paths touched by monetize PRs; covered by engine/monetize.py on main after PR #42.
_MONETIZE_PATH_PREFIXES = (
  "engine/monetize.py",
  "engine/monetization_strategy.py",
  "engine/monetize_ui.py",
  "tests/test_monetize.py",
  "tests/test_monetization_strategy.py",
  "tape_to_cloud/",
)

# ew_tool.py-only edits are common when landing monetize CLI flags.
_ALLOWED_NON_MONETIZE = frozenset({"ew_tool.py", ".gitignore", "AGENTS.md", "README.md", "reports/README.md"})


def _repo_root() -> Path:
  return Path(__file__).resolve().parent.parent


def main_has_monetize_stack() -> bool:
  root = _repo_root()
  return (root / "engine" / "monetize.py").is_file()


def _git_show_main(path: str) -> bool:
  proc = subprocess.run(
    ["git", "show", f"origin/main:{path}"],
    capture_output=True,
    text=True,
    cwd=_repo_root(),
  )
  return proc.returncode == 0


def _pr_paths(ctx: Dict[str, Any]) -> Set[str]:
  return {f.get("path") or "" for f in (ctx.get("files") or []) if f.get("path")}


def is_monetize_superseded(ctx: Dict[str, Any]) -> bool:
  """True when PR only adds monetize paths already on main."""
  if not main_has_monetize_stack():
    return False
  paths = _pr_paths(ctx)
  if not paths:
    return False
  for path in paths:
    if path in _ALLOWED_NON_MONETIZE:
      continue
    if any(path.startswith(prefix) or path == prefix for prefix in _MONETIZE_PATH_PREFIXES):
      continue
    return False
  return True


def detect_superseded_prs(
  repo: str = "",
  *,
  limit: int = 50,
  explicit_numbers: Optional[List[int]] = None,
) -> List[Dict[str, Any]]:
  """Return open PRs that look superseded (monetize dupes on main)."""
  ensure_gh_auth()
  candidates: List[Dict[str, Any]] = []

  if explicit_numbers:
    for num in explicit_numbers:
      ctx = fetch_pr_context(num, repo)
      if ctx.get("state") != "open":
        continue
      reason = "explicit"
      if is_monetize_superseded(ctx):
        reason = "explicit+monetize_on_main"
      candidates.append({
        "pr_number": num,
        "title": ctx.get("title"),
        "url": ctx.get("url"),
        "mergeable": ctx.get("mergeable"),
        "paths": sorted(_pr_paths(ctx)),
        "reason": reason,
      })
    return candidates

  for pr in list_open_prs(repo, limit=limit):
    num = int(pr["number"])
    ctx = fetch_pr_context(num, repo)
    if ctx.get("state") != "open":
      continue
    if not is_monetize_superseded(ctx):
      continue
    candidates.append({
      "pr_number": num,
      "title": ctx.get("title"),
      "url": ctx.get("url"),
      "mergeable": ctx.get("mergeable"),
      "paths": sorted(_pr_paths(ctx)),
      "reason": "monetize_on_main",
    })
  return candidates


def close_superseded_prs(
  repo: str = "",
  *,
  dry_run: bool = False,
  delete_branch: bool = False,
  explicit_numbers: Optional[List[int]] = None,
  superseded_by: int = 42,
) -> Dict[str, Any]:
  """Close superseded open PRs (default: monetize dupes after PR #42)."""
  if explicit_numbers is None:
    env_nums = os.environ.get("EW_PR_CLOSE_NUMBERS", "").strip()
    if env_nums:
      explicit_numbers = [int(x.strip()) for x in env_nums.split(",") if x.strip()]

  superseded_by = int(os.environ.get("EW_PR_SUPERSEDED_BY", str(superseded_by)))
  detected = detect_superseded_prs(repo, explicit_numbers=explicit_numbers)
  comment = (
    f"Superseded: monetize module, CLI, and UI explorer already merged to main "
    f"via PR #{superseded_by}. Closing duplicate."
  )

  results: List[Dict[str, Any]] = []
  for item in detected:
    num = int(item["pr_number"])
    entry = dict(item)
    if dry_run:
      entry["action"] = "dry_run"
      results.append(entry)
      continue
    try:
      entry["github"] = close_pr(num, repo, comment=comment, delete_branch=delete_branch)
      entry["action"] = "closed"
    except RuntimeError as exc:
      entry["action"] = "error"
      entry["error"] = str(exc)
    results.append(entry)

  return {
    "superseded_by_pr": superseded_by,
    "dry_run": dry_run,
    "main_has_monetize": main_has_monetize_stack(),
    "count": len(results),
    "results": results,
  }
