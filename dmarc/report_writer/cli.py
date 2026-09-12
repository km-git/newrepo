"""CLI: dmarc report generate --domain example.com.au --since 30d --output report.md"""

from __future__ import annotations

import argparse
import json
from pathlib import Path

from dmarc.report_writer.service import generate


def add_parser(sub: argparse._SubParsersAction) -> None:
    parser = sub.add_parser("report", help="Write Markdown + JSON review")
    inner = parser.add_subparsers(dest="report_cmd", required=True)
    gen = inner.add_parser("generate", help="Email Deliverability & Brand-Protection Review")
    gen.add_argument("--domain", required=True)
    gen.add_argument("--since", default="30d")
    gen.add_argument("--output", default=None)
    gen.add_argument("--output-dir", default=None)
    gen.add_argument("--offline", action="store_true", help="Reuse stored findings; skip live DNS")
    gen.set_defaults(handler=cmd_generate)


def cmd_generate(args: argparse.Namespace) -> int:
    result = generate(
        args.domain,
        since=args.since,
        output=Path(args.output) if args.output else None,
        root=Path(args.output_dir) if args.output_dir else None,
        run_live=not args.offline,
    )
    print(json.dumps(result, indent=2))
    return 0
