"""CLI for cost/config_drift."""

from __future__ import annotations

import argparse
from typing import Any


def register(sub: argparse._SubParsersAction[Any]) -> None:
    p = sub.add_parser("drift", help="Diff cost-relevant config vs baseline")
    p.add_argument("--provider", default="aws")
    p.add_argument("--baseline", default="")

    p.set_defaults(_cost_handler="config_drift")
