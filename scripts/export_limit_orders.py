#!/usr/bin/env python3
"""Export 250-row pair×TF limit order book from latest top50 batch JSON."""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from engine.limit_orders_export import export_limit_orders


def main() -> int:
    ap = argparse.ArgumentParser(description="Export pair×TF limit orders (250 rows)")
    ap.add_argument(
        "--input",
        type=Path,
        default=None,
        help="Batch JSON (default: output/top50_analysis_*.json newest)",
    )
    ap.add_argument("--output-dir", type=Path, default=ROOT / "output")
    ap.add_argument("--json", action="store_true", help="Also write full JSON export")
    args = ap.parse_args()

    if args.input is None:
        candidates = sorted(
            args.output_dir.glob("top50_analysis_*.json"),
            key=lambda p: p.stat().st_mtime,
            reverse=True,
        )
        if not candidates:
            print("No top50_analysis_*.json found — run scripts/run_top50_batch.py first", file=sys.stderr)
            return 1
        args.input = candidates[0]

    if not args.input.exists():
        print(f"Missing: {args.input}", file=sys.stderr)
        return 1

    batch = json.loads(args.input.read_text(encoding="utf-8"))
    result = export_limit_orders(batch, output_dir=args.output_dir, write_json=args.json)

    print(f"Input:  {args.input}")
    print(f"Rows:   {result['row_count']} (expected {result['expected_rows']})")
    print(f"CSV:    {result['csv']}")
    print(f"Latest: {result['latest_csv']}")
    print("Tiers:")
    for tier, count in sorted(result["tier_counts"].items()):
        print(f"  {tier}: {count}")
    print("Timeframes:")
    for tf, count in sorted(result["tf_counts"].items()):
        print(f"  {tf}: {count}")
    if result.get("json"):
        print(f"JSON:   {result['json']}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
