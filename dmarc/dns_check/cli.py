"""CLI: dmarc dns check --domain example.com.au"""

from __future__ import annotations

import argparse
import json
from pathlib import Path

from dmarc.dns_check.service import check_domain


def add_parser(sub: argparse._SubParsersAction) -> None:
    parser = sub.add_parser("dns", help="DNS record checker")
    inner = parser.add_subparsers(dest="dns_cmd", required=True)
    check = inner.add_parser("check", help="Look up A/AAAA/MX/TXT/DKIM/DMARC/MTA-STS/TLS-RPT/BIMI")
    check.add_argument("--domain", required=True)
    check.add_argument("--selector", action="append", default=[])
    check.add_argument("--output-dir", default=None)
    check.set_defaults(handler=cmd_check)


def cmd_check(args: argparse.Namespace) -> int:
    rows = check_domain(
        args.domain,
        selectors=args.selector or None,
        root=Path(args.output_dir) if args.output_dir else None,
    )
    print(json.dumps(rows, indent=2))
    return 0
