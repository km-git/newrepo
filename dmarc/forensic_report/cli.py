"""CLI: dmarc forensic list --since 30d"""

from __future__ import annotations

import argparse
import json
from pathlib import Path

from dmarc.forensic_report.service import list_forensic


def add_parser(sub: argparse._SubParsersAction) -> None:
    parser = sub.add_parser("forensic", help="Forensic (RUF) reports")
    inner = parser.add_subparsers(dest="forensic_cmd", required=True)
    listing = inner.add_parser("list", help="List masked RUF rows (empty is OK)")
    listing.add_argument("--domain", default=None)
    listing.add_argument("--since", default="30d")
    listing.add_argument("--output-dir", default=None)
    listing.set_defaults(handler=cmd_list)


def cmd_list(args: argparse.Namespace) -> int:
    rows = list_forensic(
        since=args.since,
        domain=args.domain,
        root=Path(args.output_dir) if args.output_dir else None,
    )
    print(
        json.dumps({"count": len(rows), "rows": rows, "note": "empty RUF is expected; many senders omit it"}, indent=2)
    )
    return 0
