#!/usr/bin/env python3
"""Architect + PR consensus bridge for coordinator service changes.

Uses existing token-saving stack (per-model 10k cap, zstd cache, EW bypass)
and OKF secondary brain for multi-model PR executive consensus.
"""

from __future__ import annotations

import argparse
import json
import os
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]


def architect_budget_check() -> dict:
  script = ROOT / "scripts" / "architect_budget_check.py"
  if not script.exists():
    return {"ok": True, "skipped": True}
  proc = subprocess.run(
    [sys.executable, str(script), "--task", "architect"],
    cwd=ROOT,
    capture_output=True,
    text=True,
  )
  return {
    "ok": proc.returncode == 0,
    "stdout": proc.stdout.strip(),
    "stderr": proc.stderr.strip(),
  }


def run_pr_consensus(pr_number: int, *, dry_run: bool = True) -> dict:
  os.environ.setdefault("EW_LLM_MAX_TOKENS_PER_MODEL", "10000")
  os.environ.setdefault("EW_OKF_BRAIN", "1")
  os.environ.setdefault("EW_BRAIN_CONSENSUS", "1")

  from engine.pr_consensus import run_pr_executive_consensus

  return run_pr_executive_consensus(pr_number, dry_run=dry_run)


def main() -> int:
  parser = argparse.ArgumentParser(description="Coordinator PR architect + consensus bridge")
  parser.add_argument("--pr", type=int, default=0, help="PR number for executive consensus")
  parser.add_argument("--approve", action="store_true", help="Apply GitHub approve (not dry-run)")
  parser.add_argument("--architect-only", action="store_true")
  args = parser.parse_args()

  budget = architect_budget_check()
  print(json.dumps({"architect_budget": budget}, indent=2))
  if not budget.get("ok", True):
    return 1
  if args.architect_only:
    return 0

  if args.pr <= 0:
    print(json.dumps({"pr_consensus": "skipped", "reason": "no --pr specified"}))
    return 0

  try:
    result = run_pr_consensus(args.pr, dry_run=not args.approve)
    print(json.dumps({"pr_consensus": result}, indent=2, default=str))
    return 0 if not result.get("error") else 2
  except Exception as exc:
    print(json.dumps({"pr_consensus_error": str(exc)}))
    return 2


if __name__ == "__main__":
  raise SystemExit(main())
