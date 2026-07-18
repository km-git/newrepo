#!/usr/bin/env python3
"""Print impact discovery report — hidden factors and balanced tweaks."""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from engine.impact_discovery import load_impact_report, run_impact_discovery


def main() -> None:
  p = argparse.ArgumentParser(description="Impact discovery report")
  p.add_argument("--refresh", action="store_true", help="Re-run discovery from tracked setups")
  args = p.parse_args()

  report = run_impact_discovery() if args.refresh else (load_impact_report() or run_impact_discovery())
  print(json.dumps(report, indent=2, default=str))


if __name__ == "__main__":
  main()
