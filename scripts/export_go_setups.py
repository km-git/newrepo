#!/usr/bin/env python3
"""Export GO + FULL-tier executable setups to CSV."""

from __future__ import annotations

import argparse
import csv
import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))


def export_go_setups(
  src: str = "output/latest_limit_orders_all_tf.csv",
  dst: str = "output/go_full_setups.csv",
) -> dict:
  rows = list(csv.DictReader(Path(src).open(encoding="utf-8")))
  selected = [
    r for r in rows
    if r.get("row_type") == "primary"
    and r.get("gtc_tier") == "executable"
    and (
      r.get("executive_verdict") == "GO"
      or r.get("honest_execution_tier") == "full"
    )
  ]
  if not selected:
    return {"exported": 0, "path": dst}

  fields = [
    "symbol", "timeframe", "direction", "executive_verdict", "honest_execution_tier",
    "readiness_score", "wae", "stop_loss", "tp1", "tp2", "tp3",
    "account_risk_pct", "dynamic_risk_mult", "dynamic_risk_factors",
    "dca_legs", "gtc_size_cap_pct",
  ]
  Path(dst).parent.mkdir(parents=True, exist_ok=True)
  with Path(dst).open("w", newline="", encoding="utf-8") as f:
    w = csv.DictWriter(f, fieldnames=fields, extrasaction="ignore")
    w.writeheader()
    w.writerows(sorted(selected, key=lambda x: (x["symbol"], x["timeframe"])))

  return {"exported": len(selected), "path": dst, "go_count": sum(1 for r in selected if r.get("executive_verdict") == "GO")}


def main() -> None:
  p = argparse.ArgumentParser(description="Export GO + FULL executable setups")
  p.add_argument("--src", default="output/latest_limit_orders_all_tf.csv")
  p.add_argument("--dst", default="output/go_full_setups.csv")
  args = p.parse_args()
  result = export_go_setups(args.src, args.dst)
  print(json.dumps(result, indent=2))


if __name__ == "__main__":
  main()
