#!/usr/bin/env python3
"""Print paths to the latest full analysis table (CSV + HTML)."""

from __future__ import annotations

import argparse
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))


def _latest(glob: str, out_dir: Path) -> Path | None:
  files = sorted(out_dir.glob(glob), key=lambda p: p.stat().st_mtime, reverse=True)
  return files[0] if files else None


def main() -> None:
  p = argparse.ArgumentParser(description="Show latest full analysis export paths")
  p.add_argument("--output-dir", default="output")
  p.add_argument("--open-html", action="store_true", help="Print HTML path for browser")
  args = p.parse_args()
  out = Path(args.output_dir)

  full = _latest("top*_full_*.csv", out) or _latest("*_full_*.csv", out)
  setups = _latest("top*_setups_*.csv", out) or _latest("*_setups_*.csv", out)
  html = _latest("top*_full_*.html", out) or _latest("*_full_*.html", out)
  detailed = _latest("top*_detailed_*.csv", out)
  outcomes = _latest("top*_outcomes_*.csv", out)

  if not any([full, detailed, outcomes]):
    print("No analysis exports found. Run:", file=sys.stderr)
    print("  PYTHONPATH=/workspace python3 scripts/run_top50_batch.py -n 50", file=sys.stderr)
    sys.exit(1)

  print("Latest analysis tables:\n")
  if full:
    print(f"  FULL (all confluences + 4 setups/pair): {full.resolve()}")
  if html:
    print(f"  HTML (browser view):                   {html.resolve()}")
  if setups:
    print(f"  SETUPS (one row per pair×style):       {setups.resolve()}")
  if detailed:
    print(f"  Detailed (waves only):                 {detailed.resolve()}")
  if outcomes:
    print(f"  Outcomes (styles only):                {outcomes.resolve()}")

  if args.open_html and html:
    print(f"\nOpen in browser: file://{html.resolve()}")


if __name__ == "__main__":
  main()
