"""CLI for cost/audit."""

from __future__ import annotations

import argparse
from typing import Any


def register(sub: argparse._SubParsersAction[Any]) -> None:
    p = sub.add_parser("inventory", help="Write cost-inventory.json")

    p.set_defaults(_cost_handler="audit")
