"""CLI for cost/compliance_map."""

from __future__ import annotations

import argparse
from typing import Any


def register(sub: argparse._SubParsersAction[Any]) -> None:
    p = sub.add_parser("compliance", help="Map observations to a framework")
    p.add_argument("--framework", default="finops-foundation")

    p.set_defaults(_cost_handler="compliance_map")
