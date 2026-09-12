"""CLI for cost/loop."""

from __future__ import annotations

import argparse
from typing import Any


def register(sub: argparse._SubParsersAction[Any]) -> None:
    p = sub.add_parser("loop", help="Run the cost watcher / monthly rollup")
    p.add_argument("--monthly", action="store_true")

    p.set_defaults(_cost_handler="loop")
