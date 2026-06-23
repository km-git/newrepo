"""Shared ccxt exchange client for funding + orderbook (Phase 2)."""

from __future__ import annotations

from typing import Optional

import ccxt

from fetchers.ccxt_fetcher import EXCHANGE_CHAIN, _make_exchange

_cached_exchange: Optional[ccxt.Exchange] = None
_cached_id: Optional[str] = None


def get_crypto_exchange(prefer: Optional[str] = None) -> Optional[ccxt.Exchange]:
  """
  Return a rate-limited ccxt exchange for market microstructure calls.
  Reuses the first working exchange from the OHLCV chain.
  """
  global _cached_exchange, _cached_id
  chain = [prefer] if prefer else []
  chain += [e for e in EXCHANGE_CHAIN if e not in chain]

  if _cached_exchange is not None and (_cached_id in chain):
    return _cached_exchange

  for ex_name in chain:
    try:
      ex = _make_exchange(ex_name)
      ex.load_markets()
      _cached_exchange = ex
      _cached_id = ex_name
      return ex
    except Exception:
      continue
  return None


def reset_exchange_cache() -> None:
  global _cached_exchange, _cached_id
  _cached_exchange = None
  _cached_id = None
