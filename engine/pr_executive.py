"""PR executive decision — rule draft + multi-model AI consensus → approve/merge."""

from __future__ import annotations

import os
from typing import Any, Dict, List, Optional, Tuple

PR_VERDICT_LADDER = ("REJECT", "REQUEST_CHANGES", "CONDITIONAL_MERGE", "APPROVE_MERGE")
PR_VERDICT_INDEX = {v: i for i, v in enumerate(PR_VERDICT_LADDER)}


def pr_executive_consensus_enabled() -> bool:
  return os.environ.get("EW_PR_EXECUTIVE_CONSENSUS", "1").lower() not in ("0", "false", "no")


def pr_auto_approve_enabled() -> bool:
  return os.environ.get("EW_PR_AUTO_APPROVE", "1").lower() not in ("0", "false", "no")


def pr_auto_merge_enabled() -> bool:
  return os.environ.get("EW_PR_AUTO_MERGE", "1").lower() not in ("0", "false", "no")


def _shift_verdict(verdict: str, steps: int) -> str:
  idx = PR_VERDICT_INDEX.get(verdict, 1)
  new_idx = max(0, min(len(PR_VERDICT_LADDER) - 1, idx + steps))
  return PR_VERDICT_LADDER[new_idx]


def pr_draft_executive(pr: Dict[str, Any]) -> Dict[str, Any]:
  """
  Rule-based draft verdict from CI, diff size, description, draft state.
  Maps to PR verdict ladder before AI panel consensus.
  """
  gaps: List[str] = []
  ci = pr.get("ci") or {}
  additions = int(pr.get("additions") or 0)
  deletions = int(pr.get("deletions") or 0)
  changed = int(pr.get("changed_files") or 0)

  if pr.get("draft"):
    gaps.append("PR is draft")
    return _executive("REQUEST_CHANGES", "low", gaps, pr)

  if os.environ.get("EW_PR_REQUIRE_CI", "1").lower() not in ("0", "false", "no"):
    if ci.get("fail"):
      gaps.append("CI checks failed")
      return _executive("REJECT", "low", gaps, pr)
    if ci.get("pending"):
      gaps.append("CI checks pending")
      return _executive("CONDITIONAL_MERGE", "medium", gaps, pr)

  if not (pr.get("body") or "").strip():
    gaps.append("Empty PR description")

  max_files = int(os.environ.get("EW_PR_MAX_FILES", "50"))
  if changed > max_files:
    gaps.append(f"Large change set ({changed} files > {max_files})")
    return _executive("CONDITIONAL_MERGE", "medium", gaps, pr)

  max_lines = int(os.environ.get("EW_PR_MAX_LINES", "3000"))
  if additions + deletions > max_lines:
    gaps.append(f"Large diff ({additions + deletions} lines)")
    return _executive("CONDITIONAL_MERGE", "medium", gaps, pr)

  test_files = [f for f in pr.get("files") or [] if _is_test_path(f.get("path", ""))]
  if changed > 5 and not test_files:
    gaps.append("No test files in PR")

  if gaps and not ci.get("pass"):
    return _executive("CONDITIONAL_MERGE", "medium", gaps, pr)

  if gaps:
    return _executive("CONDITIONAL_MERGE", "high", gaps, pr)

  return _executive("APPROVE_MERGE", "high", gaps, pr)


def _is_test_path(path: str) -> bool:
  p = path.lower()
  return "test" in p or p.startswith("tests/") or p.endswith("_test.py")


def _executive(verdict: str, conviction: str, gaps: List[str], pr: Dict[str, Any]) -> Dict[str, Any]:
  return {
    "verdict": verdict,
    "conviction": conviction,
    "direction": "MERGE",
    "playbook": f"PR #{pr.get('number')}: {pr.get('title', '')[:120]}",
    "structural_gaps": gaps,
    "position_size_pct": 100,
    "verdict_source": "rule_draft",
    "pr_number": pr.get("number"),
    "repo": pr.get("repo"),
  }


def _target_verdict_from_stance(draft: str, stance: str, escalated: bool = False) -> str:
  if stance == "unknown":
    return draft
  if stance == "agree":
    if draft == "CONDITIONAL_MERGE" and escalated:
      return "APPROVE_MERGE"
    return draft
  if stance == "caution":
    return _shift_verdict(draft, -1)
  if stance == "reject":
    return _shift_verdict(draft, -2)
  return draft


def apply_pr_ai_consensus(
  executive: Dict[str, Any],
  panel: Dict[str, Any],
) -> Tuple[Dict[str, Any], Dict[str, Any]]:
  """
  Multi-model panel consensus → final PR executive verdict + actions.
  Returns (executive, actions).
  """
  exec_out = dict(executive)
  draft = executive.get("verdict", "CONDITIONAL_MERGE")
  stance = panel.get("consensus_stance", "unknown")
  intel = panel.get("intelligence_panel") or panel
  escalated = bool(intel.get("escalated_to_premium"))
  consulted = panel.get("consulted") or intel.get("consulted") or []

  if pr_executive_consensus_enabled():
    final = _target_verdict_from_stance(draft, stance, escalated)
    exec_out["draft_verdict"] = draft
    exec_out["verdict"] = final
    exec_out["verdict_source"] = "ai_consensus"
  else:
    final = draft
    exec_out["verdict_source"] = "rule_draft"

  exec_out["llm_consensus"] = {
    "stance": stance,
    "consulted": consulted,
    "intelligence_mode": panel.get("intelligence_mode") or intel.get("intelligence_mode"),
    "escalated_to_premium": escalated,
    "disagreement_severity": intel.get("disagreement_severity"),
    "blended_summary": panel.get("blended_summary") or intel.get("blended_summary"),
    "draft_verdict": draft,
    "final_verdict": final,
  }

  summary = panel.get("blended_summary") or ""
  exec_out["playbook"] = (
    f"{executive.get('playbook', '')} [AI consensus: {stance} — {len(consulted)} models]"
    + (f" | {summary[:200]}" if summary else "")
  )

  actions = pr_actions_for_verdict(final, stance, exec_out)
  return exec_out, actions


def pr_actions_for_verdict(
  verdict: str,
  stance: str,
  executive: Dict[str, Any],
) -> Dict[str, Any]:
  """Map final verdict to GitHub actions."""
  auto_approve = pr_auto_approve_enabled()
  auto_merge = pr_auto_merge_enabled() and stance == "agree"

  actions: Dict[str, Any] = {
    "approve": False,
    "merge": False,
    "request_changes": False,
    "comment_only": True,
    "verdict": verdict,
    "stance": stance,
  }

  comment = _build_review_comment(executive)

  if verdict == "APPROVE_MERGE":
    actions["approve"] = auto_approve
    actions["merge"] = auto_merge
    actions["comment_only"] = not auto_approve
  elif verdict == "CONDITIONAL_MERGE":
    actions["approve"] = auto_approve and stance != "reject"
    actions["comment_only"] = not actions["approve"]
  elif verdict == "REQUEST_CHANGES":
    actions["request_changes"] = auto_approve
    actions["comment_only"] = not auto_approve
  elif verdict == "REJECT":
    actions["request_changes"] = auto_approve
    actions["comment_only"] = not auto_approve

  actions["comment_body"] = comment
  return actions


def _build_review_comment(executive: Dict[str, Any]) -> str:
  llm = executive.get("llm_consensus") or {}
  lines = [
    "## Executive consensus review",
    "",
    f"**Final verdict:** `{executive.get('verdict')}`",
    f"**Draft verdict:** `{executive.get('draft_verdict', executive.get('verdict'))}`",
    f"**Panel stance:** `{llm.get('stance', 'n/a')}`",
    f"**Models consulted:** {', '.join(llm.get('consulted') or []) or 'none'}",
    f"**Source:** {executive.get('verdict_source')}",
    "",
  ]
  if llm.get("blended_summary"):
    lines.extend(["**Summary:**", llm["blended_summary"], ""])
  gaps = executive.get("structural_gaps") or []
  if gaps:
    lines.append("**Structural gaps:**")
    lines.extend(f"- {g}" for g in gaps)
    lines.append("")
  lines.append("_Auto-reviewed by ew_tool multi-model executive consensus._")
  return "\n".join(lines)
