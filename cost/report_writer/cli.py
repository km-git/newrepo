"""CLI for cost/report_writer."""

from __future__ import annotations

import argparse
from typing import Any


def register(sub: argparse._SubParsersAction[Any]) -> None:
    p = sub.add_parser("report", help="Generate the review markdown + JSON")
    p.add_argument("--provider", default="all")
    p.add_argument("--since", default="30d")
    p.add_argument("--output", default="")

    p.set_defaults(_cost_handler="report_writer")
