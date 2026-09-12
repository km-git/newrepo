"""CLI for cost/azure_inventory."""

from __future__ import annotations

import argparse
from typing import Any


def register(sub: argparse._SubParsersAction[Any]) -> None:
    p = sub.add_parser("azure", help="Inventory an Azure subscription (read-only)")
    p.add_argument("--subscription-id", default="")
    p.add_argument("--tenant-id", default="")
    p.add_argument("--client-id", default="")

    p.set_defaults(_cost_handler="azure_inventory")
