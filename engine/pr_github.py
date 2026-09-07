"""GitHub PR fetch + approve/merge via gh CLI."""

from __future__ import annotations

import json
import os
import subprocess
from typing import Any, Dict, List, Optional


def _repo_slug() -> str:
  env = os.environ.get("GITHUB_REPOSITORY", "").strip()
  if env:
    return env
  proc = subprocess.run(
    ["gh", "repo", "view", "--json", "nameWithOwner", "-q", ".nameWithOwner"],
    capture_output=True,
    text=True,
  )
  if proc.returncode == 0 and proc.stdout.strip():
    return proc.stdout.strip()
  return ""


def _gh_env() -> dict:
  env = os.environ.copy()
  token = os.environ.get("GITHUB_TOKEN") or os.environ.get("GH_TOKEN")
  if token:
    env["GH_TOKEN"] = token
    env["GITHUB_TOKEN"] = token
  return env


def ensure_gh_auth() -> bool:
  """Authenticate gh CLI from GITHUB_TOKEN (GitHub Actions / cloud agents)."""
  token = os.environ.get("GITHUB_TOKEN") or os.environ.get("GH_TOKEN")
  if not token:
    return False
  proc = subprocess.run(
    ["gh", "auth", "status"],
    capture_output=True,
    text=True,
    env=_gh_env(),
  )
  if proc.returncode == 0:
    return True
  login = subprocess.run(
    ["gh", "auth", "login", "--with-token"],
    input=token,
    capture_output=True,
    text=True,
    env=_gh_env(),
  )
  return login.returncode == 0


def _gh_json(args: List[str]) -> Any:
  proc = subprocess.run(["gh"] + args, capture_output=True, text=True, env=_gh_env())
  if proc.returncode != 0:
    raise RuntimeError(proc.stderr.strip() or proc.stdout.strip() or "gh command failed")
  return json.loads(proc.stdout) if proc.stdout.strip() else {}


def _gh_run(args: List[str]) -> str:
  proc = subprocess.run(["gh"] + args, capture_output=True, text=True, env=_gh_env())
  if proc.returncode != 0:
    raise RuntimeError(proc.stderr.strip() or proc.stdout.strip() or "gh command failed")
  return proc.stdout.strip()


def _optional_ci_patterns() -> tuple:
  raw = os.environ.get(
    "EW_PR_CI_OPTIONAL",
    "executive-consensus,Cursor Approval,Approval Agent,pip-audit,bugbot,auto-approve",
  )
  return tuple(p.strip().lower() for p in raw.split(",") if p.strip())


def _is_required_ci_check(check: dict) -> bool:
  name = (check.get("name") or "").lower()
  # GitHub code-scanning rollup is named "CodeQL". Workflow jobs are "CodeQL (python)" / "CodeQL (actions)".
  if name == "codeql":
    return False
  return not any(pat in name for pat in _optional_ci_patterns())


_OK_CI_CONCLUSIONS = ("success", "skipped", "neutral", None)


def summarize_ci_checks(check_runs: List[dict]) -> Dict[str, Any]:
  """Aggregate GitHub check-runs into pass/fail/pending, ignoring advisory jobs.

  Advisory (optional) names include pip-audit continue-on-error and Cursor Bugbot
  usage-cap skips so they cannot REJECT a PR that otherwise passed required CI.
  """
  required = [c for c in check_runs if _is_required_ci_check(c)]
  completed = [c for c in required if c.get("status") == "completed"]
  ci_fail = any(c.get("conclusion") == "failure" for c in completed)
  ci_pending = any(c.get("status") in ("queued", "in_progress") for c in required)
  ci_pass = (
    bool(completed)
    and all(c.get("conclusion") in _OK_CI_CONCLUSIONS for c in completed)
    and not ci_fail
    and not ci_pending
  )
  return {
    "pass": ci_pass,
    "fail": ci_fail,
    "pending": ci_pending,
    "required": [{"name": c.get("name"), "conclusion": c.get("conclusion"), "status": c.get("status")} for c in required],
  }


def _wait_ci_enabled() -> bool:
  raw = os.environ.get("EW_PR_WAIT_CI")
  if raw is not None:
    return raw.lower() not in ("0", "false", "no")
  return bool(os.environ.get("GITHUB_ACTIONS"))


def wait_for_required_ci(
  pr_number: int,
  repo: str = "",
  *,
  timeout_s: Optional[int] = None,
  poll_s: float = 15.0,
) -> Dict[str, Any]:
  """
  Poll GitHub check-runs until required jobs finish.
  Skips this workflow itself (executive-consensus) to avoid deadlock.
  Default on in GitHub Actions so consensus does not race pytest.
  """
  import time as _time

  if not _wait_ci_enabled():
    return {"skipped": True, "reason": "EW_PR_WAIT_CI off"}

  slug = repo or _repo_slug()
  timeout_s = int(os.environ.get("EW_PR_WAIT_CI_SECONDS", str(timeout_s or 600)))
  deadline = _time.time() + timeout_s
  last: Dict[str, Any] = {}
  while _time.time() < deadline:
    pr = _gh_json(
      ["api", f"repos/{slug}/pulls/{pr_number}", "-H", "Accept: application/vnd.github+json"]
    )
    sha = (pr.get("head") or {}).get("sha") or ""
    try:
      checks = _gh_json(
        [
          "api",
          f"repos/{slug}/commits/{sha}/check-runs",
          "-H",
          "Accept: application/vnd.github+json",
        ]
      )
      check_runs = checks.get("check_runs", []) if isinstance(checks, dict) else []
    except RuntimeError:
      check_runs = []
    required = [c for c in check_runs if _is_required_ci_check(c)]
    pending = [c for c in required if c.get("status") in ("queued", "in_progress", "pending")]
    last = {
      "skipped": False,
      "pending": len(pending),
      "required": len(required),
      "names": [(c.get("name"), c.get("status"), c.get("conclusion")) for c in required[:20]],
    }
    if required and not pending:
      last["ready"] = True
      return last
    _time.sleep(poll_s)
  last["ready"] = False
  last["timeout"] = True
  return last


def _gh_paged_list(path: str, *, list_key: Optional[str] = None, per_page: int = 100, max_pages: int = 20) -> List[Any]:
  """Walk a GitHub list API that defaults to 30 items per page."""
  items: List[Any] = []
  for page in range(1, max_pages + 1):
    data = _gh_json(
      [
        "api",
        f"{path}?per_page={per_page}&page={page}",
        "-H",
        "Accept: application/vnd.github+json",
      ]
    )
    if list_key:
      if not isinstance(data, dict):
        break
      chunk = data.get(list_key) or []
    else:
      chunk = data if isinstance(data, list) else []
    if not isinstance(chunk, list):
      break
    items.extend(chunk)
    if len(chunk) < per_page:
      break
  return items


def pr_file_entries(files: List[dict]) -> List[dict]:
  """Normalize GitHub pull-file payloads for executive review (all pages)."""
  entries: List[dict] = []
  for f in files:
    path = f.get("filename") or f.get("path") or ""
    if not path:
      continue
    entries.append(
      {
        "path": path,
        "status": f.get("status"),
        "add": f.get("additions") if "additions" in f else f.get("add"),
        "del": f.get("deletions") if "deletions" in f else f.get("del"),
      }
    )
  return entries


def fetch_pr_context(pr_number: int, repo: str = "") -> Dict[str, Any]:
  """Load PR metadata, files, checks, and truncated diff for executive review."""
  slug = repo or _repo_slug()
  if not slug:
    raise RuntimeError("No GitHub repo — set GITHUB_REPOSITORY or run inside a git repo with gh auth")

  pr = _gh_json(
    [
      "api",
      f"repos/{slug}/pulls/{pr_number}",
      "-H",
      "Accept: application/vnd.github+json",
    ]
  )

  try:
    files = _gh_paged_list(f"repos/{slug}/pulls/{pr_number}/files")
  except RuntimeError:
    files = []

  try:
    check_runs = _gh_paged_list(
      f"repos/{slug}/commits/{pr['head']['sha']}/check-runs",
      list_key="check_runs",
    )
  except RuntimeError:
    check_runs = []

  diff_max = int(os.environ.get("EW_PR_DIFF_MAX_CHARS", "12000"))
  try:
    diff = _gh_run(["pr", "diff", str(pr_number), "--repo", slug])
  except RuntimeError:
    diff = ""
  if len(diff) > diff_max:
    diff = diff[:diff_max] + f"\n... [truncated {len(diff) - diff_max} chars]"

  ci = summarize_ci_checks(check_runs)

  return {
    "repo": slug,
    "number": pr_number,
    "title": pr.get("title", ""),
    "body": (pr.get("body") or "")[:4000],
    "state": pr.get("state"),
    "draft": bool(pr.get("draft")),
    "mergeable": pr.get("mergeable"),
    "additions": pr.get("additions", 0),
    "deletions": pr.get("deletions", 0),
    "changed_files": pr.get("changed_files", len(files)),
    "labels": [l.get("name") for l in pr.get("labels", [])],
    "author": (pr.get("user") or {}).get("login", ""),
    "base": (pr.get("base") or {}).get("ref", ""),
    "head": (pr.get("head") or {}).get("ref", ""),
    "head_sha": (pr.get("head") or {}).get("sha", ""),
    "files": pr_file_entries(files),
    "ci": {
      "pass": ci["pass"],
      "fail": ci["fail"],
      "pending": ci["pending"],
      "checks": [
        {"name": c.get("name"), "conclusion": c.get("conclusion"), "status": c.get("status")}
        for c in check_runs[:15]
      ],
    },
    "diff": diff,
    "url": pr.get("html_url", ""),
  }


def approve_pr(pr_number: int, repo: str = "", body: str = "") -> Dict[str, Any]:
  slug = repo or _repo_slug()
  args = ["pr", "review", str(pr_number), "--approve", "--repo", slug]
  if body:
    args.extend(["--body", body])
  out = _gh_run(args)
  return {"action": "approve", "output": out}


def dismiss_stale_change_requests(
  pr_number: int,
  repo: str = "",
  *,
  actor: str = "github-actions[bot]",
  message: str = "Stale change request: required CI is green.",
) -> Dict[str, Any]:
  """Dismiss leftover CHANGES_REQUESTED reviews from `actor`.

  GitHub Actions often cannot *approve* (org setting), but the same bot can
  dismiss its own earlier REJECT reviews so merge is no longer blocked.
  """
  slug = repo or _repo_slug()
  reviews = _gh_json(["api", f"repos/{slug}/pulls/{pr_number}/reviews"])
  dismissed: List[Dict[str, Any]] = []
  errors: List[Dict[str, Any]] = []
  if not isinstance(reviews, list):
    return {"action": "dismiss_stale_change_requests", "dismissed": dismissed, "errors": errors}
  for review in reviews:
    user = ((review.get("user") or {}).get("login") or "")
    if user != actor or review.get("state") != "CHANGES_REQUESTED":
      continue
    rid = review.get("id")
    try:
      out = _gh_run(
        [
          "api",
          "-X",
          "PUT",
          f"repos/{slug}/pulls/{pr_number}/reviews/{rid}/dismissals",
          "-f",
          f"message={message}",
          "-F",
          "event=DISMISS",
        ]
      )
      dismissed.append({"id": rid, "output": out})
    except RuntimeError as exc:
      errors.append({"id": rid, "error": str(exc)})
  return {"action": "dismiss_stale_change_requests", "dismissed": dismissed, "errors": errors}


def request_changes_pr(pr_number: int, repo: str = "", body: str = "") -> Dict[str, Any]:
  slug = repo or _repo_slug()
  args = ["pr", "review", str(pr_number), "--request-changes", "--repo", slug, "--body", body or "Changes requested by executive consensus."]
  out = _gh_run(args)
  return {"action": "request_changes", "output": out}


def comment_pr(pr_number: int, repo: str = "", body: str = "") -> Dict[str, Any]:
  slug = repo or _repo_slug()
  out = _gh_run(["pr", "comment", str(pr_number), "--repo", slug, "--body", body])
  return {"action": "comment", "output": out}


def merge_pr(pr_number: int, repo: str = "", method: str = "") -> Dict[str, Any]:
  slug = repo or _repo_slug()
  merge_method = method or os.environ.get("EW_PR_MERGE_METHOD", "squash")
  out = _gh_run(["pr", "merge", str(pr_number), "--repo", slug, f"--{merge_method}"])
  return {"action": "merge", "method": merge_method, "output": out}


def close_pr(
  pr_number: int,
  repo: str = "",
  *,
  comment: str = "",
  delete_branch: bool = False,
) -> Dict[str, Any]:
  """Close an open PR. Comment is optional (skipped when empty)."""
  slug = repo or _repo_slug()
  args = ["pr", "close", str(pr_number), "--repo", slug]
  if delete_branch:
    args.append("--delete-branch")
  out = _gh_run(args)
  result: Dict[str, Any] = {"action": "close", "output": out}
  if comment:
    try:
      result["comment"] = comment_pr(pr_number, slug, comment)
    except RuntimeError as exc:
      result["comment_error"] = str(exc)
  return result


def list_open_prs(repo: str = "", limit: int = 20) -> List[Dict[str, Any]]:
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
      "number,title,isDraft,headRefName,url,mergeable",
    ]
  )
  if not isinstance(raw, list):
    return []
  return [
    {
      "number": pr.get("number"),
      "title": pr.get("title"),
      "draft": bool(pr.get("isDraft")),
      "headRefName": pr.get("headRefName"),
      "url": pr.get("url"),
      "mergeable": pr.get("mergeable"),
    }
    for pr in raw
  ]
