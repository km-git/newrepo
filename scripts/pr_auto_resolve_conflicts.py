#!/usr/bin/env python3
<<<<<<< HEAD
"""GitHub Action entrypoint — auto-resolve merge conflicts on open PRs."""
=======
"""Auto-resolve GitHub PR merge conflicts with rules + Cursor AI."""
>>>>>>> origin/main

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

<<<<<<< HEAD
from engine.merge_conflict_resolver import resolve_all_pr_conflicts, resolve_pr_conflicts


def main() -> None:
  parser = argparse.ArgumentParser(description="Auto-resolve GitHub PR merge conflicts")
  parser.add_argument("pr_number", type=int, nargs="?", help="PR number (omit with --all)")
  parser.add_argument("--repo", default="", help="owner/repo")
  parser.add_argument("--all", action="store_true", help="Resolve all conflicted open PRs")
  parser.add_argument("--dry-run", action="store_true", help="Classify only — no push")
  parser.add_argument("--no-ai", action="store_true", help="Rule-based resolution only")
=======
from engine.pr_merge_conflict import resolve_open_pr_conflicts, resolve_pr_conflicts


def main() -> None:
  parser = argparse.ArgumentParser(description="Auto-resolve PR merge conflicts")
  parser.add_argument("pr_number", type=int, nargs="?", help="PR number (omit with --all)")
  parser.add_argument("--repo", default="", help="owner/repo")
  parser.add_argument("--all", action="store_true", help="Resolve conflicts on all open PRs")
  parser.add_argument("--dry-run", action="store_true", help="Resolve locally without commit/push")
>>>>>>> origin/main
  args = parser.parse_args()

  if not args.all and args.pr_number is None:
    parser.error("pr_number or --all required")

<<<<<<< HEAD
  use_ai = not args.no_ai
  if args.all:
    result = resolve_all_pr_conflicts(args.repo, dry_run=args.dry_run, use_ai=use_ai)
  else:
    result = resolve_pr_conflicts(args.pr_number, args.repo, dry_run=args.dry_run, use_ai=use_ai)

  print(json.dumps(result, indent=2, default=str))

  if result.get("error"):
    sys.exit(1)
  if args.all:
    if result.get("failed", 0) > 0:
      sys.exit(1)
  elif not result.get("ok") and result.get("status") not in ("clean", "no_conflicts"):
=======
  if args.all:
    result = resolve_open_pr_conflicts(repo=args.repo, dry_run=args.dry_run)
  else:
    result = resolve_pr_conflicts(args.pr_number, args.repo, dry_run=args.dry_run)

  print(json.dumps(result, indent=2, default=str))
  if result.get("error") and not result.get("skipped"):
>>>>>>> origin/main
    sys.exit(1)


if __name__ == "__main__":
  main()
