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


def _from_latest_paths(out_dir: Path) -> dict | None:
  p = out_dir / "autodream" / "latest_paths.json"
  if not p.exists():
    return None
  try:
    import json
    return json.loads(p.read_text())
  except (json.JSONDecodeError, OSError):
    return None


def main() -> None:
  p = argparse.ArgumentParser(description="Show latest full analysis export paths")
  p.add_argument("--output-dir", default="output")
  p.add_argument("--open-html", action="store_true", help="Print HTML path for browser")
  args = p.parse_args()
  out = Path(args.output_dir)

  stable_html = out / "latest_analysis.html"
  stable_csv = out / "latest_analysis.csv"
  stable_setups = out / "latest_setups_complete.csv"
  stable_setups_html = out / "latest_setups.html"
  paths_doc = _from_latest_paths(out)

  full = stable_csv if stable_csv.exists() else (_latest("top*_full_*.csv", out) or _latest("*_full_*.csv", out))
  setups = stable_setups if stable_setups.exists() else (_latest("top*_setups_*.csv", out) or _latest("*_setups_*.csv", out))
  setups_html = stable_setups_html if stable_setups_html.exists() else (_latest("latest_setups.html", out) or _latest("top*_setups_*.html", out))
  html = stable_html if stable_html.exists() else (_latest("top*_full_*.html", out) or _latest("*_full_*.html", out))
  detailed = _latest("top*_detailed_*.csv", out)
  outcomes = _latest("top*_outcomes_*.csv", out)
  md = Path("reports/TRADE_SETUPS.md")

  if not any([full, detailed, outcomes]):
    print("No analysis exports found. Run:", file=sys.stderr)
    print("  PYTHONPATH=/workspace python3 scripts/run_top50_batch.py -n 50", file=sys.stderr)
    print("  PYTHONPATH=/workspace python3 scripts/autodream_monitor.py --daemon --batch-now", file=sys.stderr)
    sys.exit(1)

  print("Latest analysis tables:\n")
  if paths_doc:
    print(f"  Scheduler updated: {paths_doc.get('updated', 'n/a')}")
  print("\n  ALL setups (executable + monitor + not_actionable):")
  if setups_html:
    print(f"  SETUPS HTML (color-coded):             {setups_html.resolve()}")
  if setups:
    print(f"  SETUPS CSV (all columns):              {setups.resolve()}")
  if md.exists():
    print(f"  TRADE SETUPS MD (in repo):             {md.resolve()}")
  print("\n  Per-pair wide table:")
  if full:
    print(f"  FULL CSV (1 row/pair):                 {full.resolve()}")
  if html:
    print(f"  FULL HTML (browser):                   {html.resolve()}")
  if detailed:
    print(f"  Detailed (waves only):                 {detailed.resolve()}")
  if outcomes:
    print(f"  Outcomes (styles only):                {outcomes.resolve()}")

  if args.open_html and setups_html:
    print(f"\nOpen setups table: file://{setups_html.resolve()}")
  elif args.open_html and html:
    print(f"\nOpen in browser: file://{html.resolve()}")


if __name__ == "__main__":
  main()
