"""CLI for cost/gcp_inventory."""

from __future__ import annotations

import argparse
from typing import Any


def register(sub: argparse._SubParsersAction[Any]) -> None:
    p = sub.add_parser("gcp", help="Inventory a GCP project (read-only)")
    p.add_argument("--project-id", default="")
    p.add_argument("--service-account", default="")

    p.set_defaults(_cost_handler="gcp_inventory")
