"""CLI for cost/rightsizing."""

from __future__ import annotations

import argparse
from typing import Any


def register(sub: argparse._SubParsersAction[Any]) -> None:
    p = sub.add_parser("rightsizing", help="Scan rightsizing observations")
    p.add_argument("--provider", default="aws")

    p.set_defaults(_cost_handler="rightsizing")
