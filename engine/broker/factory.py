"""Broker factory — paper default, live via ccxt or kraken-cli."""

from __future__ import annotations

import os
from typing import Literal

ExecutionMode = Literal["paper", "live"]
BrokerKind = Literal["auto", "ccxt", "kraken_cli", "paper_ledger"]


def execution_mode() -> ExecutionMode:
  raw = os.environ.get("EW_EXECUTION_MODE", "paper").lower().strip()
  return "live" if raw == "live" else "paper"


def broker_kind() -> BrokerKind:
  raw = os.environ.get("EW_BROKER", "auto").lower().strip()
  if raw in ("ccxt", "kraken_cli", "paper_ledger"):
    return raw  # type: ignore[return-value]
  if execution_mode() == "paper":
    from engine.broker.kraken_cli import kraken_available
    return "kraken_cli" if kraken_available() else "paper_ledger"
  from engine.broker.kraken_cli import kraken_available
  prefer = os.environ.get("EW_LIVE_BROKER", "ccxt").lower()
  if prefer == "kraken_cli" and kraken_available():
    return "kraken_cli"
  return "ccxt"


def get_broker():
  kind = broker_kind()
  if kind == "paper_ledger":
    from engine.broker import paper_ledger
    return paper_ledger
  if kind == "kraken_cli":
    from engine.broker import kraken_cli
    return kraken_cli
  from engine.broker import ccxt_broker
  return ccxt_broker
