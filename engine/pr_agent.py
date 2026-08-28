"""Cloud PR approval agent — unified entry for executive consensus auto-approve."""

from __future__ import annotations

import json
import os
from pathlib import Path
from typing import Any, Dict, List, Optional

from engine.pr_consensus import run_pr_executive_consensus
from engine.pr_github import ensure_gh_auth, list_open_prs


def _ready_open_drafts(repo: str = "") -> int:
  """Mark draft PRs ready so executive consensus can review them."""
  import subprocess

  slug = repo or ""
  try:
    proc = subprocess.run(
      ["gh", "pr", "list", "--state", "open", "--json", "number,isDraft", "-q", ".[] | select(.isDraft==true) | .number"]
      + (["--repo", slug] if slug else []),
      capture_output=True,
      text=True,
      env={**os.environ, **({"GH_TOKEN": os.environ.get("GITHUB_TOKEN", "")} if os.environ.get("GITHUB_TOKEN") else {})},
    )
    if proc.returncode != 0:
      return 0
    ready = 0
    for line in proc.stdout.splitlines():
      num = line.strip()
      if not num:
        continue
      r = subprocess.run(["gh", "pr", "ready", num] + (["--repo", slug] if slug else []), capture_output=True)
      if r.returncode == 0:
        ready += 1
    return ready
  except OSError:
    return 0


def pr_output_dir() -> Path:
  d = Path(os.environ.get("EW_PR_OUTPUT_DIR", "output/pr_reviews"))
  d.mkdir(parents=True, exist_ok=True)
  return d


def save_pr_result(result: Dict[str, Any]) -> str:
  pr_num = result.get("pr_number", 0)
  path = pr_output_dir() / f"pr-{pr_num}.json"
  path.write_text(json.dumps(result, indent=2, default=str))
  return str(path)


def run_pr_conflict_resolution(
  pr_number: Optional[int] = None,
  repo: str = "",
  *,
  dry_run: bool = False,
  approve_all: bool = False,
) -> Dict[str, Any]:
  """Resolve merge conflicts for one PR or all open PRs before executive review."""
  from engine.pr_merge_conflict import conflict_resolver_enabled, resolve_open_pr_conflicts, resolve_pr_conflicts

  if not conflict_resolver_enabled():
    return {"skipped": True, "reason": "EW_PR_AUTO_RESOLVE_CONFLICTS off"}

  if approve_all or pr_number is None:
    return resolve_open_pr_conflicts(repo=repo, dry_run=dry_run)
  return resolve_pr_conflicts(pr_number, repo, dry_run=dry_run)


def run_pr_agent(
  pr_number: Optional[int] = None,
  repo: str = "",
  *,
  dry_run: bool = False,
  use_llm: Optional[bool] = None,
  approve_all: bool = False,
) -> Dict[str, Any]:
  """
  Cloud agent entry — review one PR or all open PRs.
  Configures gh auth, runs executive consensus, persists results.
  """
  ensure_gh_auth()

  if os.environ.get("EW_PR_AUTO_RESOLVE_CONFLICTS", "1").lower() not in ("0", "false", "no"):
    try:
      conflict_result = run_pr_conflict_resolution(
        pr_number=None if approve_all else pr_number,
        repo=repo,
        dry_run=dry_run,
        approve_all=approve_all,
      )
    except Exception as exc:
      conflict_result = {"error": str(exc)}
  else:
    conflict_result = {"skipped": True}

  if approve_all:
    batch = run_pr_agent_batch(repo=repo, dry_run=dry_run, use_llm=use_llm)
    batch["conflict_resolution"] = conflict_result
    return batch

  if pr_number is None:
    raise ValueError("pr_number required unless approve_all=True")

  from engine.merge_conflict_resolver import auto_resolve_conflicts_enabled, resolve_pr_conflicts

  conflict_result: Dict[str, Any] = {}
  if auto_resolve_conflicts_enabled():
    try:
      conflict_result = resolve_pr_conflicts(pr_number, repo, dry_run=dry_run, use_ai=True)
    except Exception as exc:
      conflict_result = {"ok": False, "error": str(exc)}

  result = run_pr_executive_consensus(pr_number, repo, dry_run=dry_run, use_llm=use_llm)
  result["conflict_resolution"] = conflict_result
  path = save_pr_result(result)
  result["saved_to"] = path
  return result


def run_pr_agent_batch(
  repo: str = "",
  *,
  dry_run: bool = False,
  use_llm: Optional[bool] = None,
) -> Dict[str, Any]:
  """Review all open non-draft PRs — auto-resolve conflicts first."""
  from engine.merge_conflict_resolver import auto_resolve_conflicts_enabled, resolve_all_pr_conflicts

  conflict_summary: Dict[str, Any] = {}
  if auto_resolve_conflicts_enabled():
    try:
      conflict_summary = resolve_all_pr_conflicts(repo, dry_run=dry_run, use_ai=True)
    except Exception as exc:
      conflict_summary = {"ok": False, "error": str(exc)}

  if os.environ.get("EW_PR_READY_DRAFTS", "1").lower() not in ("0", "false", "no"):
    _ready_open_drafts(repo)
  prs = list_open_prs(repo)
  results: List[Dict[str, Any]] = []
  for pr in prs:
    if pr.get("draft"):
      continue
    num = int(pr["number"])
    try:
      r = run_pr_executive_consensus(num, repo, dry_run=dry_run, use_llm=use_llm)
      r["saved_to"] = save_pr_result(r)
      results.append(r)
    except Exception as e:
      results.append({"pr_number": num, "error": str(e)})

  summary = {
    "reviewed": len(results),
    "merged": sum(1 for r in results if any(a.get("action") == "merge" for a in r.get("github_actions", []))),
    "approved": sum(1 for r in results if any(a.get("action") == "approve" for a in r.get("github_actions", []))),
    "conflict_resolution": conflict_summary,
    "results": results,
  }
  batch_path = pr_output_dir() / "batch_latest.json"
  batch_path.write_text(json.dumps(summary, indent=2, default=str))
  summary["saved_to"] = str(batch_path)
  return summary
