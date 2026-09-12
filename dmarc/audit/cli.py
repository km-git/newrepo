"""CLI: dmarc audit inventory."""

from __future__ import annotations

import argparse
import json
from pathlib import Path

from dmarc.audit.service import run_inventory


def add_parser(sub: argparse._SubParsersAction) -> None:
    parser = sub.add_parser("audit", help="Workspace + tool inventory")
    inner = parser.add_subparsers(dest="audit_cmd", required=True)
    inv = inner.add_parser("inventory", help="Write dmarc-inventory.json")
    inv.add_argument("--output-dir", default=None)
    inv.set_defaults(handler=cmd_inventory)


def cmd_inventory(args: argparse.Namespace) -> int:
    payload = run_inventory(Path(args.output_dir) if args.output_dir else None)
    print(json.dumps(payload, indent=2))
    return 0
