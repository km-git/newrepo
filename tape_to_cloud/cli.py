"""CLI: python -m tape_to_cloud report [module|job-pack]."""

from __future__ import annotations

import argparse
import json
import sys

from tape_to_cloud.catalog import MODULES
from tape_to_cloud.sample_reports import get_report, list_reports


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(prog="python -m tape_to_cloud", description="Tape-to-cloud demo reports")
    sub = parser.add_subparsers(dest="cmd", required=True)
    report = sub.add_parser("report", help="Print a sample module or job-pack report as JSON")
    report.add_argument("module", nargs="?", default="job-pack", help="module id or job-pack (default job-pack)")
    listing = sub.add_parser("list", help="List sample reports")
    listing.add_argument("--json", action="store_true")
    args = parser.parse_args(argv)
    if args.cmd == "list":
        rows = list_reports()
        if args.json:
            print(json.dumps(rows, indent=2))
        else:
            for row in rows:
                print(f"{row['module']:16} {row['report_id']}  {row['href']}")
        return 0
    try:
        payload = get_report(args.module)
    except KeyError:
        print(f"unknown module: {args.module}", file=sys.stderr)
        print("known:", ", ".join((*MODULES, "job-pack")), file=sys.stderr)
        return 2
    print(json.dumps(payload, indent=2, default=str))
    return 0
