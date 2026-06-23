#!/usr/bin/env python3
"""Print SMC institutional edge analysis from latest batch."""

from __future__ import annotations

import argparse
import json
from collections import Counter
from pathlib import Path


def find_latest() -> Path:
  candidates = sorted(
    Path("output").glob("top*_analysis_*.json"),
    key=lambda p: p.stat().st_mtime,
    reverse=True,
  )
  for p in candidates:
    if "top50" in p.name or "top20" in p.name:
      return p
  return candidates[0]


def main() -> None:
  ap = argparse.ArgumentParser()
  ap.add_argument("--json", type=str, default="")
  args = ap.parse_args()
  path = Path(args.json) if args.json else find_latest()
  data = json.loads(path.read_text())

  grades = Counter()
  status = Counter()
  entry_signals = []
  executables = []

  for r in data:
    if r.get("status") == "incomplete":
      continue
    s = (r.get("step8_outcomes") or {}).get("setups", {}).get("smc", {})
    if not s:
      continue
    grades[s.get("entry_grade", "?")] += 1
    status[s.get("status", "?")] += 1
    if s.get("entry_signal"):
      entry_signals.append({
        "symbol": r["symbol"],
        "tf": s.get("timeframe"),
        "dir": s.get("direction"),
        "grade": s.get("entry_grade"),
        "conf": s.get("confluence_count"),
        "score": s.get("institutional_score"),
      })
    if s.get("status") == "executable":
      executables.append({
        "symbol": r["symbol"],
        "tier": s.get("execution_tier"),
        "grade": s.get("entry_grade"),
        "reason": (s.get("honest_reason") or "")[:100],
      })

  print(f"SMC Analysis — {path.name} ({len(data)} pairs)\n")
  print("Grades:", dict(grades))
  print("Status:", dict(status))
  print(f"\nEntry signals: {len(entry_signals)}/50")
  for e in entry_signals:
    print(f"  {e['symbol']:14} {e['tf']:4} {e['dir']:5} grade={e['grade']} conf={e['conf']} score={e['score']}")
  print(f"\nExecutable: {len(executables)}")
  for e in executables:
    print(f"  {e['symbol']:14} {e['tier']:5} grade={e['grade']} — {e['reason']}")

  audit = Path("output/autodream/system_audit.json")
  if audit.exists():
    a = json.loads(audit.read_text())
    print(f"\nSystem audit: {a['verdict']['status']}")
    for w in a["verdict"].get("warnings", [])[:6]:
      print(f"  WARN: {w}")
    bp = a.get("setups", {}).get("by_path", {})
    if bp.get("smc"):
      print(f"  SMC OOS avg: {bp['smc'].get('oos_avg')}")
    if bp.get("ew"):
      print(f"  EW OOS avg: {bp['ew'].get('oos_avg')}")


if __name__ == "__main__":
  main()
