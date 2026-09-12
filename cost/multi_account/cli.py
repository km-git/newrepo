"""CLI for cost/multi_account."""

from __future__ import annotations

import argparse
from typing import Any


def register(sub: argparse._SubParsersAction[Any]) -> None:
    p = sub.add_parser("multi-account", help="Aggregate c7n-org dry-run output")
    p.add_argument("--accounts", default="")

    p.set_defaults(_cost_handler="multi_account")
