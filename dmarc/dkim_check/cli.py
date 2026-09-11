"""CLI: dmarc dkim check --domain example.com.au --selector google"""

from __future__ import annotations

import argparse
import json
from pathlib import Path

from dmarc.dkim_check.service import check_domain


def add_parser(sub: argparse._SubParsersAction) -> None:
    parser = sub.add_parser("dkim", help="DKIM record checker")
    inner = parser.add_subparsers(dest="dkim_cmd", required=True)
    check = inner.add_parser("check", help="Look up selector._domainkey TXT")
    check.add_argument("--domain", required=True)
    check.add_argument("--selector", default=None)
    check.add_argument("--output-dir", default=None)
    check.set_defaults(handler=cmd_check)


def cmd_check(args: argparse.Namespace) -> int:
    rows = check_domain(
        args.domain,
        selector=args.selector,
        root=Path(args.output_dir) if args.output_dir else None,
    )
    print(json.dumps(rows, indent=2))
    return 0
