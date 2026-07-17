#!/usr/bin/env python3
"""Execute limit orders from export CSV — paper default."""

from __future__ import annotations

import argparse
import json
import os
import sys

from engine.execution_agent import execute_from_csv, execution_status


def main() -> None:
  parser = argparse.ArgumentParser(description="Execute EW limit order export")
  parser.add_argument("--csv", default="output/latest_limit_orders_all_tf.csv")
  parser.add_argument("--live", action="store_true", help="Live mode (needs EW_EXECUTE_CONFIRM=1)")
  parser.add_argument("--max-orders", type=int, default=0)
  parser.add_argument("--status", action="store_true")
  args = parser.parse_args()

  if args.status:
    print(json.dumps(execution_status(), indent=2))
    return

  if args.live:
    os.environ["EW_EXECUTION_MODE"] = "live"
  result = execute_from_csv(args.csv, dry_run=not args.live, max_orders=args.max_orders or 0)
  print(json.dumps(result, indent=2, default=str))
  sys.exit(0 if result.get("ok") else 1)


if __name__ == "__main__":
  main()
