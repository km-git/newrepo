"""CLI for cost/cost_explorer."""

from __future__ import annotations

import argparse
from typing import Any


def register(sub: argparse._SubParsersAction[Any]) -> None:
    p = sub.add_parser("cost-explorer", help="Roll up daily/monthly cost")
    p.add_argument("--provider", default="aws")
    p.add_argument("--since", default="30d")

    p.set_defaults(_cost_handler="cost_explorer")
