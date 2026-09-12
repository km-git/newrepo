"""CLI: dmarc spf parse --domain example.com.au"""

from __future__ import annotations

import argparse
import json
from pathlib import Path

from dmarc.spf_parser.service import parse_domain


def add_parser(sub: argparse._SubParsersAction) -> None:
    parser = sub.add_parser("spf", help="SPF record parser")
    inner = parser.add_subparsers(dest="spf_cmd", required=True)
    parse = inner.add_parser("parse", help="Parse SPF and count DNS lookups")
    parse.add_argument("--domain", required=True)
    parse.add_argument("--output-dir", default=None)
    parse.set_defaults(handler=cmd_parse)


def cmd_parse(args: argparse.Namespace) -> int:
    print(json.dumps(parse_domain(args.domain, root=Path(args.output_dir) if args.output_dir else None), indent=2))
    return 0
