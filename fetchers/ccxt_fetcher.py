"""Crypto OHLCV fetcher with exchange fallback chain."""

from __future__ import annotations

import time
from typing import Dict, List

import ccxt
import pandas as pd

from cache.disk_cache import get_cache

EXCHANGE_CHAIN = ["okx", "bybit", "kraken", "binance"]

TF_MAP = {
  "1w": "1w",
  "1d": "1d",
  "4h": "4h",
  "1h": "1h",
  "15m": "15m",
}


def _make_exchange(name: str):
  cls = getattr(ccxt, name)
  return cls({"enableRateLimit": True})


def _symbol_for_exchange(symbol: str, exchange_id: str) -> str:
  """Normalize BTC/USDT for exchange-specific formats."""
  base, quote = symbol.split("/")
  if exchange_id == "kraken":
    # Kraken uses XBT for BTC
    if base.upper() == "BTC":
      base = "XBT"
  return f"{base}/{quote}"


def fetch_ohlcv_crypto(symbol: str, timeframes: List[str], limit: int = 500) -> Dict[str, pd.DataFrame]:
  cache = get_cache()
  cached, hit = cache.get_or_compute(
    "ohlcv_crypto",
    lambda: _fetch_ohlcv_crypto_uncached(symbol, timeframes, limit),
    symbol,
    tuple(timeframes),
    limit,
  )
  if hit:
    print(f"[cache] HIT ohlcv_crypto {symbol} tfs={timeframes}")
  return cached


def _fetch_ohlcv_crypto_uncached(
  symbol: str, timeframes: List[str], limit: int = 500
) -> Dict[str, pd.DataFrame]:
  last_err = None
  for ex_name in EXCHANGE_CHAIN:
    try:
      ex = _make_exchange(ex_name)
      ex_sym = _symbol_for_exchange(symbol, ex_name)
      out: Dict[str, pd.DataFrame] = {}
      for tf in timeframes:
        ccxt_tf = TF_MAP.get(tf, tf)
        bars = ex.fetch_ohlcv(ex_sym, timeframe=ccxt_tf, limit=limit)
        if not bars:
          raise ValueError(f"No bars for {ex_sym} {ccxt_tf}")
        df = pd.DataFrame(bars, columns=["timestamp", "Open", "High", "Low", "Close", "Volume"])
        df["timestamp"] = pd.to_datetime(df["timestamp"], unit="ms", utc=True)
        df = df.set_index("timestamp")
        out[tf] = df
        print(f"[fetch] {ex_name} {ex_sym} {tf}: {len(df)} bars, last={df['Close'].iloc[-1]:.2f}")
        time.sleep(ex.rateLimit / 1000 if ex.rateLimit else 0.2)
      return out
    except Exception as e:
      last_err = e
      print(f"[fetch] {ex_name} failed: {e}")
      continue
  raise RuntimeError(f"All exchanges failed for {symbol}: {last_err}")
