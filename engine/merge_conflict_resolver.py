"""Automated GitHub merge conflict detection, AI classification, and resolution."""

from __future__ import annotations

import os
import re
import subprocess
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple

from engine.pr_github import _gh_env, _gh_json, _repo_slug, comment_pr, ensure_gh_auth, list_open_prs


CONFLICT_START = re.compile(r"^<<<<<<< ")
CONFLICT_MID = re.compile(r"^=======$")
CONFLICT_END = re.compile(r"^>>>>>>> ")


@dataclass
class ConflictHunk:
  ours: str
  theirs: str
  marker_ours: str
  marker_theirs: str


def auto_resolve_conflicts_enabled() -> bool:
  return os.environ.get("EW_PR_AUTO_RESOLVE_CONFLICTS", "1").lower() not in ("0", "false", "no")


def _git_run(args: List[str], *, cwd: Optional[Path] = None, check: bool = True) -> subprocess.CompletedProcess:
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


def list_conflicted_prs(repo: str = "", limit: int = 30) -> List[Dict[str, Any]]:
  """Open PRs with merge conflicts against base branch."""
  slug = repo or _repo_slug()
  raw = _gh_json(
    [
      "pr",
      "list",
      "--repo",
      slug,
      "--state",
      "open",
      "--limit",
      str(limit),
      "--json",
      "number,title,isDraft,headRefName,baseRefName,mergeable,mergeStateStatus,url",
    ]
  )
  if not isinstance(raw, list):
    return []
  conflicted = []
  for pr in raw:
    status = str(pr.get("mergeStateStatus") or "").upper()
    mergeable = pr.get("mergeable")
    if status in ("DIRTY", "CONFLICTING") or mergeable is False:
      conflicted.append(
        {
          "number": pr.get("number"),
          "title": pr.get("title"),
          "draft": bool(pr.get("isDraft")),
          "headRefName": pr.get("headRefName"),
          "baseRefName": pr.get("baseRefName") or "main",
          "mergeStateStatus": status or "UNKNOWN",
          "url": pr.get("url"),
        }
      )
  return conflicted


def parse_conflict_hunks(content: str) -> List[ConflictHunk]:
  lines = content.splitlines(keepends=True)
  hunks: List[ConflictHunk] = []
  i = 0
  while i < len(lines):
    if not CONFLICT_START.match(lines[i]):
      i += 1
      continue
    marker_ours = lines[i].rstrip("\n")
    i += 1
    ours: List[str] = []
    while i < len(lines) and not CONFLICT_MID.match(lines[i]):
      ours.append(lines[i])
      i += 1
    if i >= len(lines):
      break
    i += 1  # skip =======
    theirs: List[str] = []
    while i < len(lines) and not CONFLICT_END.match(lines[i]):
      theirs.append(lines[i])
      i += 1
    if i >= len(lines):
      break
    marker_theirs = lines[i].rstrip("\n")
    i += 1
    hunks.append(
      ConflictHunk(
        ours="".join(ours),
        theirs="".join(theirs),
        marker_ours=marker_ours,
        marker_theirs=marker_theirs,
      )
    )
  return hunks


def has_conflict_markers(content: str) -> bool:
  return "<<<<<<<" in content


def _normalize_ws(text: str) -> str:
  return "\n".join(line.rstrip() for line in text.strip().splitlines())


def classify_conflict_file(path: str, content: str) -> Dict[str, Any]:
  """Classify file conflicts as simple (auto-fix) or complicated (AI + report)."""
  hunks = parse_conflict_hunks(content)
  if not hunks:
    return {"path": path, "classification": "clean", "hunks": 0, "reasons": []}

  reasons: List[str] = []
  complicated = 0
  for h in hunks:
    o, t = h.ours.strip(), h.theirs.strip()
    if not o or not t:
      reasons.append("one_side_empty")
      continue
    if o == t or _normalize_ws(o) == _normalize_ws(t):
      reasons.append("identical_sides")
      continue
    if path.endswith((".md", ".mdc", ".txt", ".json", ".yml", ".yaml", ".sh")):
      reasons.append("config_or_docs")
      continue
  complicated = sum(
    1
    for h in hunks
    if h.ours.strip() and h.theirs.strip() and _normalize_ws(h.ours) != _normalize_ws(h.theirs)
    and not path.endswith((".md", ".mdc", ".txt", ".json", ".yml", ".yaml", ".sh"))
  )
  classification = "complicated" if complicated else "simple"
  return {
    "path": path,
    "classification": classification,
    "hunks": len(hunks),
    "complicated_hunks": complicated,
    "reasons": reasons,
  }


def _rule_resolve_hunk(hunk: ConflictHunk, path: str) -> Optional[str]:
  o, t = hunk.ours.strip(), hunk.theirs.strip()
  if not o:
    return hunk.theirs
  if not t:
    return hunk.ours
  if o == t or _normalize_ws(o) == _normalize_ws(t):
    return hunk.ours
  return None


def rule_resolve_content(path: str, content: str) -> Tuple[Optional[str], List[str]]:
  """Apply deterministic rules; return resolved content if all hunks resolved."""
  if not has_conflict_markers(content):
    return content, []

  lines = content.splitlines(keepends=True)
  out: List[str] = []
  actions: List[str] = []
  i = 0
  while i < len(lines):
    if not CONFLICT_START.match(lines[i]):
      out.append(lines[i])
      i += 1
      continue

    marker_ours = lines[i].rstrip("\n")
    i += 1
    ours_lines: List[str] = []
    while i < len(lines) and not CONFLICT_MID.match(lines[i]):
      ours_lines.append(lines[i])
      i += 1
    if i >= len(lines):
      return None, actions
    i += 1
    theirs_lines: List[str] = []
    while i < len(lines) and not CONFLICT_END.match(lines[i]):
      theirs_lines.append(lines[i])
      i += 1
    if i >= len(lines):
      return None, actions
    marker_theirs = lines[i].rstrip("\n")
    i += 1

    hunk = ConflictHunk(
      ours="".join(ours_lines),
      theirs="".join(theirs_lines),
      marker_ours=marker_ours,
      marker_theirs=marker_theirs,
    )
    resolved = _rule_resolve_hunk(hunk, path)
    if resolved is None:
      return None, actions
    out.append(resolved if resolved.endswith("\n") else resolved + "\n")
    actions.append("rule")

  result = "".join(out)
  if has_conflict_markers(result):
    return None, actions
  return result, actions


def ai_resolve_content(path: str, content: str) -> Tuple[Optional[str], str]:
  """Use Cursor Pro (Composer) to resolve remaining conflict markers."""
  from engine.llm_advisor import _call_advisory, advisory_credentials_available

  if not advisory_credentials_available():
    return None, "no_llm_credentials"

  max_chars = int(os.environ.get("EW_CONFLICT_AI_MAX_CHARS", "24000"))
  body = content if len(content) <= max_chars else content[:max_chars] + "\n... [truncated]"

  prompt = f"""You are resolving a git merge conflict in `{path}`.

RULES:
- Remove ALL conflict markers (<<<<<<<, =======, >>>>>>>).
- Preserve correct behavior from BOTH branches where complementary.
- Prefer Cursor Pro routing (98% Composer/Grok), cheap-first, executive-only Other Models.
- Keep Elliott Wave / risk logic deterministic; do not weaken tests.
- Return ONLY the full resolved file content — no markdown fences, no commentary.

CONFLICTED FILE:
{body}
"""
  resp = _call_advisory("composer", "composer-2.5", "cheap", "workhorse", 8000, prompt, context="routine")
  if not resp.get("available") or not resp.get("summary"):
    return None, str(resp.get("error") or resp.get("skipped") or "ai_unavailable")

  resolved = resp["summary"].strip()
  if resolved.startswith("```"):
    resolved = re.sub(r"^```[\w]*\n?", "", resolved)
    resolved = re.sub(r"\n?```$", "", resolved)

  if has_conflict_markers(resolved):
    return None, "ai_left_markers"
  return resolved, "ai_composer"


def resolve_file_conflicts(path: str, content: str, *, use_ai: bool = True) -> Dict[str, Any]:
  info = classify_conflict_file(path, content)
  if info["classification"] == "clean":
    return {"path": path, "status": "clean", "classification": "clean", "content": content}

  resolved, actions = rule_resolve_content(path, content)
  method = "rules"
  if resolved is None and use_ai:
    resolved, ai_note = ai_resolve_content(path, content)
    actions.append(ai_note)
    method = "ai"
  elif resolved is None:
    return {
      "path": path,
      "status": "failed",
      "classification": info["classification"],
      "reason": "rules_insufficient",
      "info": info,
    }

  return {
    "path": path,
    "status": "resolved",
    "classification": info["classification"],
    "method": method,
    "actions": actions,
    "info": info,
    "content": resolved,
  }


def _conflicted_files_in_repo() -> List[str]:
  proc = _git_run(["diff", "--name-only", "--diff-filter=U"], check=False)
  if proc.returncode != 0:
    return []
  return [f.strip() for f in proc.stdout.splitlines() if f.strip()]


def resolve_branch_conflicts(
  branch: str,
  *,
  base: str = "main",
  repo: str = "",
  dry_run: bool = False,
  use_ai: bool = True,
) -> Dict[str, Any]:
  """
  Fetch, merge base into branch, resolve conflicts, commit and push.
  """
  ensure_gh_auth()
  slug = repo or _repo_slug()
  remote = os.environ.get("EW_GIT_REMOTE", "origin")
  result: Dict[str, Any] = {
    "branch": branch,
    "base": base,
    "repo": slug,
    "dry_run": dry_run,
    "files": [],
    "complicated": [],
    "ok": False,
  }

  _git_run(["fetch", remote, base, branch])
  _git_run(["checkout", branch])
  merge_proc = _git_run(["merge", f"{remote}/{base}", "--no-commit", "--no-ff"], check=False)

  conflicted = _conflicted_files_in_repo()
  if not conflicted:
    if merge_proc.returncode != 0:
      _git_run(["merge", "--abort"], check=False)
      result["status"] = "merge_failed"
      result["error"] = (merge_proc.stderr or merge_proc.stdout or "").strip()
      return result
    msg = os.environ.get(
      "EW_CONFLICT_COMMIT_MSG",
      f"Merge {base} into {branch} — sync with base (no conflicts)",
    )
    if dry_run:
      _git_run(["merge", "--abort"], check=False)
      result["ok"] = True
      result["status"] = "dry_run_clean_merge"
      return result
    _git_run(["commit", "-m", msg])
    _git_run(["push", remote, branch])
    result["ok"] = True
    result["status"] = "pushed_clean_merge"
    return result

  resolved_all = True
  for rel in conflicted:
    fpath = Path(rel)
    if not fpath.exists():
      result["files"].append({"path": rel, "status": "missing"})
      resolved_all = False
      continue
    raw = fpath.read_text(encoding="utf-8", errors="replace")
    file_result = resolve_file_conflicts(rel, raw, use_ai=use_ai)
    result["files"].append(file_result)
    if file_result.get("classification") == "complicated":
      result["complicated"].append(rel)
    if file_result.get("status") != "resolved":
      resolved_all = False
      continue
    if not dry_run:
      fpath.write_text(file_result["content"], encoding="utf-8")

  if not resolved_all:
    _git_run(["merge", "--abort"], check=False)
    result["status"] = "unresolved"
    return result

  if dry_run:
    _git_run(["merge", "--abort"], check=False)
    result["ok"] = True
    result["status"] = "dry_run_resolved"
    return result

  _git_run(["add", "-A"])
  msg = os.environ.get(
    "EW_CONFLICT_COMMIT_MSG",
    f"Merge {base} into {branch} — auto-resolve conflicts (Cursor Pro AI)",
  )
  _git_run(["commit", "-m", msg])
  _git_run(["push", remote, branch])
  result["ok"] = True
  result["status"] = "pushed"
  return result


def resolve_pr_conflicts(
  pr_number: int,
  repo: str = "",
  *,
  dry_run: bool = False,
  use_ai: bool = True,
) -> Dict[str, Any]:
  """Resolve merge conflicts for one PR branch, comment on PR, return report."""
  from engine.pr_github import fetch_pr_context

  ensure_gh_auth()
  pr = fetch_pr_context(pr_number, repo)
  branch = pr.get("head") or pr.get("headRefName", "")
  base = pr.get("base") or "main"
  slug = pr.get("repo") or repo or _repo_slug()

  out = resolve_branch_conflicts(branch, base=base, repo=slug, dry_run=dry_run, use_ai=use_ai)
  out["pr_number"] = pr_number
  out["url"] = pr.get("url")

  if not dry_run and out.get("ok") and out.get("status") == "pushed":
    complicated = out.get("complicated") or []
    body = (
      f"🤖 **Auto-resolved merge conflicts** with Cursor Pro AI (`{branch}` ← `{base}`).\n\n"
      f"- Files: {len(out.get('files') or [])}\n"
      f"- Complicated (AI-merged): {', '.join(complicated) if complicated else 'none'}\n"
    )
    try:
      comment_pr(pr_number, slug, body)
    except RuntimeError:
      pass

  return out


def resolve_all_pr_conflicts(
  repo: str = "",
  *,
  dry_run: bool = False,
  use_ai: bool = True,
) -> Dict[str, Any]:
  """Resolve conflicts on all open conflicted PRs."""
  prs = list_conflicted_prs(repo)
  results: List[Dict[str, Any]] = []
  for pr in prs:
    if pr.get("draft"):
      continue
    num = int(pr["number"])
    try:
      results.append(resolve_pr_conflicts(num, repo, dry_run=dry_run, use_ai=use_ai))
    except Exception as exc:
      results.append({"pr_number": num, "ok": False, "error": str(exc)})

  summary = {
    "conflicted_prs": len(prs),
    "processed": len(results),
    "resolved": sum(1 for r in results if r.get("ok")),
    "failed": sum(1 for r in results if not r.get("ok")),
    "complicated_reports": [
      {"pr": r.get("pr_number"), "files": r.get("complicated")}
      for r in results
      if r.get("complicated")
    ],
    "results": results,
  }
  out_dir = Path(os.environ.get("EW_PR_OUTPUT_DIR", "output/pr_reviews"))
  out_dir.mkdir(parents=True, exist_ok=True)
  path = out_dir / "conflict_resolution_latest.json"
  path.write_text(__import__("json").dumps(summary, indent=2, default=str), encoding="utf-8")
  summary["saved_to"] = str(path)
  return summary
