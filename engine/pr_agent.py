"""Cloud PR approval agent — unified entry for executive consensus auto-approve."""

from __future__ import annotations

import json
import os
from pathlib import Path
from typing import Any, Dict, List, Optional

from engine.pr_consensus import run_pr_executive_consensus
from engine.pr_github import ensure_gh_auth, list_open_prs


def pr_output_dir() -> Path:
  d = Path(os.environ.get("EW_PR_OUTPUT_DIR", "output/pr_reviews"))
  d.mkdir(parents=True, exist_ok=True)
  return d


def save_pr_result(result: Dict[str, Any]) -> str:
  pr_num = result.get("pr_number", 0)
  path = pr_output_dir() / f"pr-{pr_num}.json"
  path.write_text(json.dumps(result, indent=2, default=str))
  return str(path)


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

  if approve_all:
    return run_pr_agent_batch(repo=repo, dry_run=dry_run, use_llm=use_llm)

  if pr_number is None:
    raise ValueError("pr_number required unless approve_all=True")

  result = run_pr_executive_consensus(pr_number, repo, dry_run=dry_run, use_llm=use_llm)
  path = save_pr_result(result)
  result["saved_to"] = path
  return result


def run_pr_agent_batch(
  repo: str = "",
  *,
  dry_run: bool = False,
  use_llm: Optional[bool] = None,
) -> Dict[str, Any]:
  """Review all open non-draft PRs."""
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
    "results": results,
  }
  batch_path = pr_output_dir() / "batch_latest.json"
  batch_path.write_text(json.dumps(summary, indent=2, default=str))
  summary["saved_to"] = str(batch_path)
  return summary
