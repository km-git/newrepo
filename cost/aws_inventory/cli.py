"""CLI for cost/aws_inventory."""

from __future__ import annotations

import argparse
from typing import Any


def register(sub: argparse._SubParsersAction[Any]) -> None:
    p = sub.add_parser("aws", help="Inventory an AWS account (read-only)")
    p.add_argument("--profile", default="")
    p.add_argument("--regions", default="ap-southeast-2")

    p.set_defaults(_cost_handler="aws_inventory")
