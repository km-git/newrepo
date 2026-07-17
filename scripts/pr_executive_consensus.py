#!/usr/bin/env python3
"""Cloud PR approval agent — multi-model executive consensus, auto-approve/merge."""

from __future__ import annotations

import argparse
import json
import sys

from engine.pr_agent import run_pr_agent


def main() -> None:
  parser = argparse.ArgumentParser(description="PR approval cloud agent")
  parser.add_argument("pr_number", type=int, nargs="?", help="PR number (omit with --all)")
  parser.add_argument("--repo", default="", help="owner/repo")
  parser.add_argument("--all", action="store_true", help="Review all open PRs")
  parser.add_argument("--dry-run", action="store_true", help="Decision only — no GitHub actions")
  parser.add_argument("--no-llm", action="store_true", help="Rule-based draft only")
  parser.add_argument("--force", action="store_true", help="Ignore cache")
  args = parser.parse_args()

  if not args.all and args.pr_number is None:
    parser.error("pr_number or --all required")

  result = run_pr_agent(
    pr_number=args.pr_number,
    repo=args.repo,
    dry_run=args.dry_run,
    use_llm=not args.no_llm,
    approve_all=args.all,
  )
  print(json.dumps(result, indent=2, default=str))

  if result.get("error"):
    sys.exit(1)
  if not args.all:
    verdict = (result.get("executive") or {}).get("verdict", "")
    if verdict == "REJECT":
      sys.exit(2)


if __name__ == "__main__":
  main()
