"""CLI for cost/untagged."""

from __future__ import annotations

import argparse
from typing import Any


def register(sub: argparse._SubParsersAction[Any]) -> None:
    p = sub.add_parser("untagged", help="Scan untagged resources")
    p.add_argument("--tagging-policy", default="")

    p.set_defaults(_cost_handler="untagged")
