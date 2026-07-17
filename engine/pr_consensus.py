"""Orchestrate PR executive consensus: draft → AI panel → approve/merge."""

from __future__ import annotations

import json
import os
from typing import Any, Dict, Optional

from engine.pr_cache import get_cached_review, set_cached_review
from engine.pr_executive import (
  apply_pr_ai_consensus,
  pr_actions_for_verdict,
  pr_draft_executive,
  pr_executive_consensus_enabled,
)
from engine.pr_github import (
  approve_pr,
  comment_pr,
  ensure_gh_auth,
  fetch_pr_context,
  merge_pr,
  request_changes_pr,
)
from engine.pr_llm_advisor import get_pr_llm_advisory


def run_pr_executive_consensus(
  pr_number: int,
  repo: str = "",
  *,
  dry_run: bool = False,
  use_llm: Optional[bool] = None,
  force: bool = False,
) -> Dict[str, Any]:
  """
  Full pipeline:
  1. Fetch PR context (GitHub)
  2. Rule-based draft executive verdict
  3. Multi-model AI panel consensus (5/7 approve rule when expanded)
  4. Auto-approve / merge / request-changes per final verdict
  """
  ensure_gh_auth()
  pr = fetch_pr_context(pr_number, repo)
  head_sha = pr.get("head_sha", "")

  if not force and not dry_run:
    cached = get_cached_review(pr_number, pr.get("repo", repo), head_sha)
    if cached:
      cached = dict(cached)
      cached["cache_hit"] = True
      print(f"[pr] cache hit #{pr_number} @ {head_sha[:8]}")
      return cached

  draft = pr_draft_executive(pr)
  llm_on = use_llm if use_llm is not None else os.environ.get("EW_PR_LLM_ADVISORY", "1").lower() not in ("0", "false", "no")
  panel = get_pr_llm_advisory(pr, draft, enabled=llm_on) or {}

  if panel.get("consensus_stance") and pr_executive_consensus_enabled():
    executive, actions = apply_pr_ai_consensus(draft, panel)
  else:
    executive = dict(draft)
    actions = pr_actions_for_verdict(draft["verdict"], panel.get("consensus_stance", "unknown"), executive)

  result: Dict[str, Any] = {
    "pr_number": pr_number,
    "repo": pr.get("repo"),
    "url": pr.get("url"),
    "head_sha": head_sha,
    "draft_executive": draft,
    "executive": executive,
    "panel": panel,
    "actions": actions,
    "dry_run": dry_run,
    "cache_hit": False,
    "github_actions": [],
  }

  if dry_run:
    print(
      f"[pr] dry-run #{pr_number}: verdict={executive['verdict']} "
      f"stance={panel.get('consensus_stance')} votes={panel.get('vote_tally')} "
      f"approve={actions.get('approve')} merge={actions.get('merge')}"
    )
    return result

  slug = pr.get("repo", "")
  try:
    if actions.get("request_changes"):
      result["github_actions"].append(request_changes_pr(pr_number, slug, actions["comment_body"]))
    elif actions.get("approve"):
      result["github_actions"].append(approve_pr(pr_number, slug, actions["comment_body"]))
    elif actions.get("comment_only"):
      result["github_actions"].append(comment_pr(pr_number, slug, actions["comment_body"]))

    if actions.get("merge"):
      result["github_actions"].append(merge_pr(pr_number, slug))
      print(f"[pr] merged #{pr_number} ({executive['verdict']})")
    else:
      print(
        f"[pr] reviewed #{pr_number}: verdict={executive['verdict']} "
        f"approve={actions.get('approve')} merge={actions.get('merge')}"
      )
  except RuntimeError as e:
    result["error"] = str(e)
    print(f"[pr] GitHub action failed: {e}")

  set_cached_review(pr_number, slug, head_sha, result)
  return result


def pr_consensus_summary(result: Dict[str, Any]) -> str:
  return json.dumps(
    {
      "verdict": result.get("executive", {}).get("verdict"),
      "stance": result.get("panel", {}).get("consensus_stance"),
      "vote_tally": result.get("panel", {}).get("vote_tally"),
      "actions": result.get("actions"),
      "github_actions": [a.get("action") for a in result.get("github_actions", [])],
      "cache_hit": result.get("cache_hit"),
    },
    indent=2,
  )
