"""Orchestrate PR executive consensus: draft → AI panel → approve/merge."""

from __future__ import annotations

import json
import os
from typing import Any, Dict, Optional

from engine.pr_executive import (
  apply_pr_ai_consensus,
  pr_draft_executive,
  pr_executive_consensus_enabled,
)
from engine.pr_github import (
  approve_pr,
  comment_pr,
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
) -> Dict[str, Any]:
  """
  Full pipeline:
  1. Fetch PR context (GitHub)
  2. Rule-based draft executive verdict
  3. Multi-model AI panel consensus (if credentials + enabled)
  4. Auto-approve / merge / request-changes per final verdict
  """
  pr = fetch_pr_context(pr_number, repo)
  executive = pr_draft_executive(pr)

  llm_on = use_llm if use_llm is not None else os.environ.get("EW_PR_LLM_ADVISORY", "1").lower() not in ("0", "false", "no")
  panel = get_pr_llm_advisory(pr, executive, enabled=llm_on) or {}

  if panel.get("consensus_stance") and pr_executive_consensus_enabled():
    executive, actions = apply_pr_ai_consensus(executive, panel)
  else:
    from engine.pr_executive import pr_actions_for_verdict

    actions = pr_actions_for_verdict(executive["verdict"], panel.get("consensus_stance", "unknown"), executive)

  result: Dict[str, Any] = {
    "pr_number": pr_number,
    "repo": pr.get("repo"),
    "url": pr.get("url"),
    "draft_executive": pr_draft_executive(pr),
    "executive": executive,
    "panel": panel,
    "actions": actions,
    "dry_run": dry_run,
    "github_actions": [],
  }

  if dry_run:
    print(
      f"[pr] dry-run #{pr_number}: verdict={executive['verdict']} "
      f"stance={panel.get('consensus_stance')} approve={actions.get('approve')} merge={actions.get('merge')}"
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

  return result


def pr_consensus_summary(result: Dict[str, Any]) -> str:
  return json.dumps(
    {
      "verdict": result.get("executive", {}).get("verdict"),
      "stance": result.get("panel", {}).get("consensus_stance"),
      "actions": result.get("actions"),
      "github_actions": [a.get("action") for a in result.get("github_actions", [])],
    },
    indent=2,
  )
