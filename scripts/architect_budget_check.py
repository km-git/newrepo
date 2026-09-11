#!/usr/bin/env python3
"""Check GPT-5.6 architect/decision call fits 10K token budget."""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from engine.architect_budget import (
  ARCHITECT_TOKEN_CEILING,
  TokenBudgetExceeded,
  prepare_decision_call,
  token_saver_checklist,
)
from tools.github_context import fetch_github_summary


def main() -> int:
  p = argparse.ArgumentParser(description="GPT-5.6 architect budget check")
  p.add_argument("--task", default="architect", choices=["advise", "decision", "architect", "planning"])
  p.add_argument("--isc", default="Ship MVP in 14 days with Stripe billing")
  p.add_argument("--repo", default="", help="GitHub owner/repo for context")
  p.add_argument("--no-cache", action="store_true")
  args = p.parse_args()

  payload = {"isc": args.isc, "stack": ["next.js", "supabase", "stripe"]}
  ctx = ""
  if args.repo:
    gh = fetch_github_summary(args.repo)
    ctx = json.dumps(gh, separators=(",", ":"))

  try:
    pkg = prepare_decision_call(
      args.task,
      payload,
      extra_context=ctx,
      use_cache=not args.no_cache,
    )
  except TokenBudgetExceeded as e:
    print(f"BUDGET EXCEEDED: {e}", file=sys.stderr)
    return 1

  print(json.dumps({
    "ceiling": ARCHITECT_TOKEN_CEILING,
    "model": pkg["model"],
    "budget": pkg["budget"],
    "route_reason": pkg.get("route_reason"),
    "cache_hit": pkg["budget"].get("cache_hit"),
    "token_savers": token_saver_checklist(),
    "prompt_preview": pkg["prompt"][:400],
  }, indent=2))
  return 0


if __name__ == "__main__":
  raise SystemExit(main())
