"""Unified data fetch dispatcher."""

from __future__ import annotations

from typing import Dict, List, Optional

import pandas as pd

from fetchers.ccxt_fetcher import fetch_ohlcv_crypto
from fetchers.yf_fetcher import fetch_ohlcv_yf


def fetch(
  symbol: str,
  timeframes: List[str],
  is_crypto: bool,
  exchange_preference: Optional[str] = None,
) -> Dict[str, pd.DataFrame]:
  if is_crypto:
    return fetch_ohlcv_crypto(symbol, timeframes, exchange_preference=exchange_preference)
  return fetch_ohlcv_yf(symbol, timeframes)
