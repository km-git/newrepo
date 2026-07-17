"""Normalize symbols across analysis (BTC/USDT) and exchange wire formats."""

from __future__ import annotations

import re
from typing import Dict, Tuple

# Kraken spot uses XBT not BTC; USD not USDT on many pairs
KRAKEN_QUOTE_MAP = {"USDT": "USD", "USDC": "USD"}
KRAKEN_BASE_MAP = {"BTC": "XBT"}


def split_pair(symbol: str) -> Tuple[str, str]:
  s = symbol.strip().upper().replace("-", "/")
  if "/" in s:
    base, quote = s.split("/", 1)
    return base, quote
  for quote in ("USDT", "USDC", "USD", "EUR"):
    if s.endswith(quote) and len(s) > len(quote):
      return s[: -len(quote)], quote
  return s, "USDT"


def canonical_symbol(symbol: str) -> str:
  base, quote = split_pair(symbol)
  if base == "XBT":
    base = "BTC"
  return f"{base}/{quote}"


def for_ccxt(symbol: str, exchange_id: str) -> str:
  base, quote = split_pair(symbol)
  ex = exchange_id.lower()
  if ex == "kraken":
    base = KRAKEN_BASE_MAP.get(base, base)
    quote = KRAKEN_QUOTE_MAP.get(quote, quote)
  return f"{base}/{quote}"


def for_kraken_cli(symbol: str) -> str:
  """Kraken CLI pair e.g. XBTUSD, ETHUSD."""
  base, quote = split_pair(symbol)
  base = KRAKEN_BASE_MAP.get(base, base)
  quote = KRAKEN_QUOTE_MAP.get(quote, quote)
  return f"{base}{quote}"


def client_order_id(symbol: str, timeframe: str, leg: int, suffix: str = "") -> str:
  sym = re.sub(r"[^A-Z0-9]", "", canonical_symbol(symbol).replace("/", ""))[:8]
  tf = re.sub(r"[^a-z0-9]", "", timeframe.lower())[:4]
  base = f"ew-{sym}-{tf}-L{leg}"
  return (base + suffix)[:36]
