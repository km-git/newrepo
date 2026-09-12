"""CLI: dmarc inbox test --from ... --to a,b,c"""

from __future__ import annotations

import argparse
import json
from pathlib import Path

from dmarc.inbox_placement.service import run_test


def add_parser(sub: argparse._SubParsersAction) -> None:
    parser = sub.add_parser("inbox", help="Inbox placement tester")
    inner = parser.add_subparsers(dest="inbox_cmd", required=True)
    test = inner.add_parser("test", help="Heuristic seed-account placement (dry-run default)")
    test.add_argument("--from-addr", dest="from_addr", required=True)
    test.add_argument("--to", default="", help="Comma-separated seed mailboxes")
    test.add_argument("--subject", default="Deliverability seed probe")
    test.add_argument("--live", action="store_true", help="Actually SMTP-send (needs DMARC_SMTP_*)")
    test.add_argument("--output-dir", default=None)
    test.set_defaults(handler=cmd_test)


def cmd_test(args: argparse.Namespace) -> int:
    recipients = [part.strip() for part in args.to.split(",") if part.strip()]
    rows = run_test(
        args.from_addr,
        recipients,
        subject=args.subject,
        dry_run=not args.live,
        root=Path(args.output_dir) if args.output_dir else None,
    )
    print(json.dumps({"rows": rows, "note": "heuristic; run weekly and track the trend"}, indent=2))
    return 0
