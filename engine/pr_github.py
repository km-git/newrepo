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

  files = _gh_json(
    [
      "api",
      f"repos/{slug}/pulls/{pr_number}/files",
      "-H",
      "Accept: application/vnd.github+json",
    ]
  )
  if not isinstance(files, list):
    files = []

  try:
    checks = _gh_json(
      [
        "api",
        f"repos/{slug}/commits/{pr['head']['sha']}/check-runs",
        "-H",
        "Accept: application/vnd.github+json",
      ]
    )
    check_runs = checks.get("check_runs", [])
  except RuntimeError:
    check_runs = []

  diff_max = int(os.environ.get("EW_PR_DIFF_MAX_CHARS", "12000"))
  try:
    diff = _gh_run(["pr", "diff", str(pr_number), "--repo", slug])
  except RuntimeError:
    diff = ""
  if len(diff) > diff_max:
    diff = diff[:diff_max] + f"\n... [truncated {len(diff) - diff_max} chars]"

  ci_pass = all(c.get("conclusion") in ("success", "skipped", None) for c in check_runs if c.get("status") == "completed")
  ci_fail = any(c.get("conclusion") == "failure" for c in check_runs)
  ci_pending = any(c.get("status") in ("queued", "in_progress") for c in check_runs)

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
    "files": [
      {"path": f.get("filename"), "status": f.get("status"), "add": f.get("additions"), "del": f.get("deletions")}
      for f in files[:40]
    ],
    "ci": {
      "pass": ci_pass and not ci_fail and not ci_pending,
      "fail": ci_fail,
      "pending": ci_pending,
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


def list_open_prs(repo: str = "", limit: int = 20) -> List[Dict[str, Any]]:
  slug = repo or _repo_slug()
  raw = _gh_json(["pr", "list", "--repo", slug, "--state", "open", "--limit", str(limit), "--json", "number,title,draft,headRefName,url"])
  if isinstance(raw, list):
    return raw
  return []
