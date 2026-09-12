"""CLI: dmarc ingest pull --imap-host ... or --from-dir / fixtures."""

from __future__ import annotations

import argparse
import json
from pathlib import Path

from dmarc.dmarc_ingest.service import ingest_directory, ingest_fixtures, ingest_imap


def add_parser(sub: argparse._SubParsersAction) -> None:
    parser = sub.add_parser("ingest", help="DMARC aggregate (RUA) ingest")
    inner = parser.add_subparsers(dest="ingest_cmd", required=True)
    pull = inner.add_parser("pull", help="Pull RUA reports from IMAP, a directory, or fixtures")
    pull.add_argument("--imap-host", default="")
    pull.add_argument("--imap-user", default="")
    pull.add_argument("--imap-pass", default="", help="Ignored; set DMARC_IMAP_PASS instead")
    pull.add_argument("--imap-folder", default="INBOX")
    pull.add_argument("--from-dir", default=None)
    pull.add_argument("--fixtures", action="store_true")
    pull.add_argument("--output-dir", default=None)
    pull.set_defaults(handler=cmd_pull)


def cmd_pull(args: argparse.Namespace) -> int:
    root = Path(args.output_dir) if args.output_dir else None
    if args.imap_pass:
        print("warning: --imap-pass is ignored; use DMARC_IMAP_PASS")
    if args.imap_host:
        rows = ingest_imap(args.imap_host, args.imap_user, folder=args.imap_folder, root=root)
    elif args.from_dir:
        rows = ingest_directory(Path(args.from_dir), root=root)
    else:
        rows = ingest_fixtures(root=root)
    print(json.dumps({"count": len(rows), "rows": rows}, indent=2))
    return 0
