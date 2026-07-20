#!/usr/bin/env python3
"""Run full end-to-end trading cycle: learn → analyze → export → execute → improve."""

from __future__ import annotations

import argparse
import json
import os
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from engine.llm_backend import bootstrap_llm_env

bootstrap_llm_env()

from engine.e2e_pipeline import e2e_status, run_e2e_cycle


def main() -> None:
  parser = argparse.ArgumentParser(description="E2E trading analysis cycle")
  parser.add_argument("--batch-n", type=int, default=50, help="Top N pairs (0 = monitor only)")
  parser.add_argument("--no-batch", action="store_true", help="Skip batch analysis")
  parser.add_argument("--monitor-only", action="store_true", help="Monitor queue only")
  parser.add_argument("--execute", action="store_true", help="Paper execute executable rows")
  parser.add_argument("--execute-live", action="store_true", help="Live execute (needs EW_EXECUTE_CONFIRM=1)")
  parser.add_argument("--llm", action="store_true", help="Enable LLM advisory on batch")
  parser.add_argument("--status", action="store_true", help="Show E2E status only")
  parser.add_argument("--health", action="store_true", help="Run health checks only")
  args = parser.parse_args()

  if args.status:
    print(json.dumps(e2e_status(), indent=2, default=str))
    return

  if args.health:
    from engine.system_health import run_health_checks, save_health
    h = run_health_checks()
    print(json.dumps(h, indent=2, default=str))
    print(f"saved: {save_health(h)}", file=sys.stderr)
    sys.exit(0 if h.get("healthy") else 1)

  result = run_e2e_cycle(
    batch_n=0 if args.monitor_only else args.batch_n,
    skip_batch=args.no_batch or args.monitor_only,
    skip_monitor=False,
    force_batch=not args.no_batch and not args.monitor_only and args.batch_n > 0,
    llm_advisory=args.llm,
    execute=args.execute,
    execute_live=args.execute_live,
  )
  print(json.dumps(result, indent=2, default=str))
  sys.exit(0 if result.get("ok") and result.get("healthy") else 1)


if __name__ == "__main__":
  main()
