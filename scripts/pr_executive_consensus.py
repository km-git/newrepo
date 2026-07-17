#!/usr/bin/env python3
"""Run multi-model executive consensus on a GitHub PR — auto-approve/merge when GO."""

from __future__ import annotations

import argparse
import json
import sys

from engine.pr_consensus import run_pr_executive_consensus


def main() -> None:
  parser = argparse.ArgumentParser(description="PR executive consensus — multi-model auto-approve")
  parser.add_argument("pr_number", type=int, help="Pull request number")
  parser.add_argument("--repo", default="", help="owner/repo (default: current gh repo)")
  parser.add_argument("--dry-run", action="store_true", help="Decision only — no GitHub actions")
  parser.add_argument("--no-llm", action="store_true", help="Rule-based draft only, skip AI panel")
  args = parser.parse_args()

  result = run_pr_executive_consensus(
    args.pr_number,
    args.repo,
    dry_run=args.dry_run,
    use_llm=not args.no_llm,
  )
  print(json.dumps(result, indent=2, default=str))
  if result.get("error"):
    sys.exit(1)
  verdict = result.get("executive", {}).get("verdict", "")
  if verdict == "REJECT":
    sys.exit(2)


if __name__ == "__main__":
  main()
