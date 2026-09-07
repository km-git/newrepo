#!/usr/bin/env python3
"""Close open PRs superseded by code already on main (monetize dupes, etc.)."""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from engine.pr_superseded import close_superseded_prs


def main() -> None:
  parser = argparse.ArgumentParser(description="Close superseded open PRs")
  parser.add_argument("pr_numbers", type=int, nargs="*", help="PR numbers (omit to auto-detect)")
  parser.add_argument("--repo", default="", help="owner/repo")
  parser.add_argument("--dry-run", action="store_true", help="Detect only, do not close")
  parser.add_argument("--delete-branch", action="store_true", help="Delete head branch after close")
  parser.add_argument("--superseded-by", type=int, default=42, help="Merged PR that landed the canonical code")
  args = parser.parse_args()

  result = close_superseded_prs(
    args.repo,
    dry_run=args.dry_run,
    delete_branch=args.delete_branch,
    explicit_numbers=args.pr_numbers or None,
    superseded_by=args.superseded_by,
  )
  print(json.dumps(result, indent=2, default=str))
  if any(r.get("action") == "error" for r in result.get("results", [])):
    sys.exit(1)


if __name__ == "__main__":
  main()
