"""Auto-detect and resolve GitHub PR merge conflicts via rules + Cursor AI."""

from __future__ import annotations

import json
import os
import re
import subprocess
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple

from engine.pr_github import _gh_env, _gh_json, _repo_slug, comment_pr, ensure_gh_auth

CONFLICT_RE = re.compile(
  r"<<<<<<<[^\n]*\n(.*?)=======\n(.*?)>>>>>>>[^\n]*",
  re.DOTALL,
)

MERGE_CONFLICT_SYSTEM = (
  "Git merge conflict resolver for a Python trading codebase. "
  "Given OURS (PR branch) and THEIRS (base branch), return merged code that preserves "
  "intent of BOTH sides when complementary. Drop duplicate blocks. "
  "JSON only: {resolved: string, classification: simple|complicated, rationale: string}"
)


def conflict_resolver_enabled() -> bool:
  return os.environ.get("EW_PR_AUTO_RESOLVE_CONFLICTS", "1").lower() not in ("0", "false", "no")


def conflict_llm_enabled() -> bool:
  return os.environ.get("EW_PR_CONFLICT_LLM", "1").lower() not in ("0", "false", "no")


def max_conflict_hunks_per_file() -> int:
  return int(os.environ.get("EW_PR_CONFLICT_MAX_HUNKS", "8"))


def max_conflicted_files() -> int:
  return int(os.environ.get("EW_PR_CONFLICT_MAX_FILES", "12"))


@dataclass
class ConflictHunk:
  full_match: str
  ours: str
  theirs: str


def parse_conflict_hunks(text: str) -> List[ConflictHunk]:
  return [
    ConflictHunk(full_match=m.group(0), ours=m.group(1), theirs=m.group(2))
    for m in CONFLICT_RE.finditer(text)
  ]


def has_conflict_markers(text: str) -> bool:
  return "<<<<<<<" in text and "=======" in text and ">>>>>>>" in text


def _assignment_lhs(line: str) -> Optional[str]:
  match = re.match(r"^\s*([A-Za-z_][\w]*)\s*=", line.strip())
  return match.group(1) if match else None


def _lines_disjoint_union(ours: str, theirs: str) -> Optional[str]:
  ours_lines = [ln for ln in ours.splitlines() if ln.strip()]
  theirs_lines = [ln for ln in theirs.splitlines() if ln.strip()]
  if not ours_lines or not theirs_lines:
    return None
  ours_set = {ln.strip() for ln in ours_lines}
  theirs_set = {ln.strip() for ln in theirs_lines}
  if ours_set & theirs_set:
    return None
  ours_lhs = {_assignment_lhs(ln) for ln in ours_lines}
  theirs_lhs = {_assignment_lhs(ln) for ln in theirs_lines}
  if (ours_lhs - {None}) & (theirs_lhs - {None}):
    return None
  merged: List[str] = []
  seen = set()
  for ln in ours_lines + theirs_lines:
    key = ln.strip()
    if key in seen:
      continue
    seen.add(key)
    merged.append(ln)
  return "\n".join(merged) + ("\n" if ours.endswith("\n") or theirs.endswith("\n") else "")


def _rule_resolve_hunk(hunk: ConflictHunk) -> Tuple[Optional[str], str]:
  ours = hunk.ours
  theirs = hunk.theirs
  if ours.strip() == theirs.strip():
    return ours, "identical"
  if not ours.strip():
    return theirs, "take_theirs"
  if not theirs.strip():
    return ours, "take_ours"
  union = _lines_disjoint_union(ours, theirs)
  if union is not None:
    return union, "union_lines"
  if ours.strip() in theirs:
    return theirs, "theirs_superset"
  if theirs.strip() in ours:
    return ours, "ours_superset"
  return None, "needs_ai"


def _llm_resolve_hunk(path: str, hunk: ConflictHunk, repo_context: str = "") -> Tuple[Optional[str], str]:
  if not conflict_llm_enabled():
    return None, "llm_disabled"
  try:
    from engine.llm_advisor import call_llm_task

    payload = {
      "file": path,
      "ours": hunk.ours[:6000],
      "theirs": hunk.theirs[:6000],
      "repo_context": repo_context[:2000],
    }
    prompt = f"{MERGE_CONFLICT_SYSTEM}\n\nDATA:{json.dumps(payload, separators=(',', ':'))}\n\nJSON:"
    resp = call_llm_task("architect", prompt)
    if not resp.get("available"):
      return None, f"llm_unavailable:{resp.get('error', resp.get('skipped', 'unknown'))}"
    resolved = str(resp.get("resolved") or "")
    classification = str(resp.get("classification") or "complicated")
    if not resolved:
      raw = str(resp.get("summary") or resp.get("text") or resp.get("raw") or "")
      raw = raw.strip()
      if raw.startswith("```"):
        raw = raw.split("```", 2)[1]
        if raw.startswith("json"):
          raw = raw[4:]
        raw = raw.strip()
      if raw.startswith("{"):
        try:
          parsed = json.loads(raw)
          resolved = str(parsed.get("resolved") or "")
          classification = str(parsed.get("classification") or classification)
        except json.JSONDecodeError:
          pass
    if not resolved or classification == "complicated":
      return None, "llm_complicated"
    if has_conflict_markers(resolved):
      return None, "llm_left_markers"
    return resolved, "ai_resolved"
  except Exception as exc:
    return None, f"llm_error:{exc}"


def resolve_file_conflicts(
  path: str,
  content: str,
  *,
  repo_context: str = "",
) -> Tuple[Optional[str], List[Dict[str, str]]]:
  hunks = parse_conflict_hunks(content)
  if not hunks:
    return content, []
  if len(hunks) > max_conflict_hunks_per_file():
    return None, [{"strategy": "too_many_hunks", "count": str(len(hunks))}]

  resolved_text = content
  actions: List[Dict[str, str]] = []
  for hunk in hunks:
    merged, strategy = _rule_resolve_hunk(hunk)
    if merged is None:
      merged, strategy = _llm_resolve_hunk(path, hunk, repo_context=repo_context)
    if merged is None:
      actions.append({"strategy": strategy, "status": "unresolved"})
      return None, actions
    resolved_text = resolved_text.replace(hunk.full_match, merged, 1)
    actions.append({"strategy": strategy, "status": "resolved"})

  if has_conflict_markers(resolved_text):
    actions.append({"strategy": "markers_remain", "status": "unresolved"})
    return None, actions
  return resolved_text, actions


def classify_file_resolution(actions: List[Dict[str, str]]) -> str:
  strategies = {a.get("strategy", "") for a in actions}
  if any(a.get("status") == "unresolved" for a in actions):
    return "complicated"
  if any(s in ("ai_resolved", "llm_complicated") for s in strategies):
    return "ai_resolved"
  return "simple"


def _run_git(args: List[str], *, cwd: Optional[Path] = None, check: bool = True) -> subprocess.CompletedProcess[str]:
  proc = subprocess.run(
    ["git"] + args,
    capture_output=True,
    text=True,
    cwd=str(cwd) if cwd else None,
    env=_gh_env(),
  )
  if check and proc.returncode != 0:
    raise RuntimeError((proc.stderr or proc.stdout or "git failed").strip())
  return proc


def _ensure_git_identity() -> None:
  name = os.environ.get("EW_GIT_USER_NAME", "ew-autonomous-bot")
  email = os.environ.get("EW_GIT_USER_EMAIL", "ew-bot@users.noreply.github.com")
  _run_git(["config", "user.name", name], check=False)
  _run_git(["config", "user.email", email], check=False)


def fetch_pr_merge_state(pr_number: int, repo: str = "") -> Dict[str, Any]:
  slug = repo or _repo_slug()
  pr = _gh_json(["api", f"repos/{slug}/pulls/{pr_number}", "-H", "Accept: application/vnd.github+json"])
  return {
    "repo": slug,
    "number": pr_number,
    "mergeable": pr.get("mergeable"),
    "mergeable_state": pr.get("mergeable_state"),
    "state": pr.get("state"),
    "base": (pr.get("base") or {}).get("ref", "main"),
    "head": (pr.get("head") or {}).get("ref", ""),
    "head_sha": (pr.get("head") or {}).get("sha", ""),
    "url": pr.get("html_url", ""),
    "title": pr.get("title", ""),
  }


def _list_conflicted_files() -> List[str]:
  proc = _run_git(["diff", "--name-only", "--diff-filter=U"], check=False)
  if proc.returncode != 0:
    return []
  return [ln.strip() for ln in proc.stdout.splitlines() if ln.strip()]


def _attempt_merge(base_ref: str) -> Tuple[bool, str]:
  """Run merge; return (has_conflicts, combined_output)."""
  proc = _run_git(["merge", f"origin/{base_ref}", "--no-commit", "--no-ff"], check=False)
  out = (proc.stdout or "") + (proc.stderr or "")
  if proc.returncode == 0:
    return False, out
  if "CONFLICT" in out or _list_conflicted_files():
    return True, out
  raise RuntimeError(out.strip() or "git merge failed")


def _abort_merge() -> None:
  _run_git(["merge", "--abort"], check=False)


def _commit_resolution(message: str) -> str:
  _run_git(["add", "-A"])
  proc = _run_git(["commit", "-m", message], check=False)
  if proc.returncode != 0 and "nothing to commit" in (proc.stdout + proc.stderr):
    return ""
  if proc.returncode != 0:
    raise RuntimeError((proc.stderr or proc.stdout).strip())
  return _run_git(["rev-parse", "HEAD"]).stdout.strip()


def _push_branch(branch: str) -> None:
  _run_git(["push", "origin", f"HEAD:{branch}"])


def resolve_pr_conflicts(
  pr_number: int,
  repo: str = "",
  *,
  dry_run: bool = False,
) -> Dict[str, Any]:
  """
  Merge base into PR head, auto-resolve conflicts, commit and push.
  Returns structured result with per-file classification.
  """
  ensure_gh_auth()
  if not conflict_resolver_enabled():
    return {"pr_number": pr_number, "skipped": True, "reason": "EW_PR_AUTO_RESOLVE_CONFLICTS off"}

  state = fetch_pr_merge_state(pr_number, repo)
  slug = state["repo"]
  base = state["base"] or "main"
  head = state["head"]
  result: Dict[str, Any] = {
    "pr_number": pr_number,
    "repo": slug,
    "url": state.get("url"),
    "base": base,
    "head": head,
    "dry_run": dry_run,
    "files": [],
    "resolved": False,
    "pushed": False,
  }

  if state.get("mergeable") is True:
    result["skipped"] = True
    result["reason"] = "already_mergeable"
    return result
  if not head:
    result["error"] = "missing head ref"
    return result

  _ensure_git_identity()
  _run_git(["fetch", "origin", base, head])
  _run_git(["checkout", head])
  _run_git(["pull", "--ff-only", "origin", head], check=False)

  has_conflicts, _merge_out = _attempt_merge(base)
  if not has_conflicts:
    if dry_run:
      _run_git(["merge", "--abort"], check=False)
      result["skipped"] = True
      result["reason"] = "clean_merge"
      return result
    commit_msg = f"Merge {base} into {head} (PR #{pr_number})"
    sha = _commit_resolution(commit_msg)
    result["commit"] = sha
    result["resolved"] = True
    result["reason"] = "clean_merge"
    _push_branch(head)
    result["pushed"] = True
    return result

  conflicted = _list_conflicted_files()
  if len(conflicted) > max_conflicted_files():
    _abort_merge()
    result["error"] = f"too many conflicted files ({len(conflicted)} > {max_conflicted_files()})"
    result["conflicted_files"] = conflicted
    return result

  repo_context = f"PR #{pr_number}: {state.get('title', '')[:120]}"
  resolved_files: List[Dict[str, Any]] = []
  complicated: List[str] = []

  for rel in conflicted:
    path = Path(rel)
    if not path.exists():
      complicated.append(rel)
      resolved_files.append({"path": rel, "classification": "complicated", "reason": "missing_worktree"})
      continue
    original = path.read_text(encoding="utf-8", errors="replace")
    merged, actions = resolve_file_conflicts(rel, original, repo_context=repo_context)
    classification = classify_file_resolution(actions)
    entry = {"path": rel, "classification": classification, "actions": actions}
    resolved_files.append(entry)
    if merged is None or classification == "complicated":
      complicated.append(rel)
      continue
    path.write_text(merged, encoding="utf-8")

  result["files"] = resolved_files
  if complicated:
    _abort_merge()
    result["error"] = f"complicated conflicts remain in {len(complicated)} file(s)"
    result["complicated_files"] = complicated
    if not dry_run:
      body = _build_conflict_comment(result, failed=True)
      try:
        comment_pr(pr_number, slug, body)
        result["commented"] = True
      except RuntimeError as exc:
        result["comment_error"] = str(exc)
    return result

  if dry_run:
    _abort_merge()
    result["resolved"] = True
    result["reason"] = "dry_run"
    return result

  commit_msg = (
    f"Auto-resolve merge conflicts with {base} (PR #{pr_number})\n\n"
    f"Resolved {len(resolved_files)} file(s) via rules + Cursor AI."
  )
  sha = _commit_resolution(commit_msg)
  result["commit"] = sha
  result["resolved"] = True
  _push_branch(head)
  result["pushed"] = True
  try:
    comment_pr(pr_number, slug, _build_conflict_comment(result, failed=False))
    result["commented"] = True
  except RuntimeError as exc:
    result["comment_error"] = str(exc)
  return result


def _build_conflict_comment(result: Dict[str, Any], *, failed: bool) -> str:
  lines = [
    "## Merge conflict auto-resolution",
    "",
    f"**PR:** #{result.get('pr_number')}",
    f"**Base:** `{result.get('base')}`",
    f"**Head:** `{result.get('head')}`",
    "",
  ]
  if failed:
    lines.extend([
      "**Status:** blocked — complicated conflicts need manual review",
      "",
      f"**Complicated files:** {', '.join(result.get('complicated_files') or [])}",
      "",
      "_Re-run after manual fix or reduce conflict scope._",
    ])
  else:
    lines.extend([
      "**Status:** resolved and pushed",
      "",
      f"**Commit:** `{result.get('commit', '')[:12]}`",
      "",
      "| File | Classification |",
      "| --- | --- |",
    ])
    for f in result.get("files") or []:
      lines.append(f"| `{f.get('path')}` | {f.get('classification')} |")
    lines.append("")
    lines.append("_Auto-resolved by ew_tool conflict agent (rules + Cursor Pro)._")
  return "\n".join(lines)


def resolve_open_pr_conflicts(
  repo: str = "",
  *,
  dry_run: bool = False,
  limit: int = 20,
) -> Dict[str, Any]:
  from engine.pr_github import list_open_prs

  prs = list_open_prs(repo, limit=limit)
  results: List[Dict[str, Any]] = []
  for pr in prs:
    num = int(pr["number"])
    try:
      state = fetch_pr_merge_state(num, repo)
      if state.get("mergeable") is True:
        results.append({"pr_number": num, "skipped": True, "reason": "already_mergeable"})
        continue
      results.append(resolve_pr_conflicts(num, repo, dry_run=dry_run))
    except Exception as exc:
      results.append({"pr_number": num, "error": str(exc)})
  return {
    "reviewed": len(results),
    "resolved": sum(1 for r in results if r.get("resolved")),
    "pushed": sum(1 for r in results if r.get("pushed")),
    "results": results,
  }
