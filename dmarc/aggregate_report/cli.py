"""CLI: dmarc aggregate report --since 30d"""

from __future__ import annotations

import argparse
import json
from pathlib import Path

from dmarc.aggregate_report.service import run_report


def add_parser(sub: argparse._SubParsersAction) -> None:
    parser = sub.add_parser("aggregate", help="Aggregate RUA report")
    inner = parser.add_subparsers(dest="aggregate_cmd", required=True)
    report = inner.add_parser("report", help="Write standalone HTML charts")
    report.add_argument("--domain", default=None)
    report.add_argument("--since", default="30d")
    report.add_argument("--output-dir", default=None)
    report.set_defaults(handler=cmd_report)


def cmd_report(args: argparse.Namespace) -> int:
    summary = run_report(
        domain=args.domain,
        since=args.since,
        root=Path(args.output_dir) if args.output_dir else None,
    )
    print(json.dumps(summary, indent=2))
    return 0
