"""Tradfi OHLCV fetcher via yfinance."""

from __future__ import annotations

from typing import Dict, List

import pandas as pd
import yfinance as yf

from cache.disk_cache import get_cache

YF_INTERVAL = {
  "1w": "1wk",
  "1d": "1d",
  "4h": "4h",
  "1h": "1h",
  "15m": "15m",
}

YF_PERIOD = {
  "1w": "5y",
  "1d": "2y",
  "4h": "730d",
  "1h": "730d",
  "15m": "60d",
}


def _unwrap_columns(df: pd.DataFrame) -> pd.DataFrame:
  if isinstance(df.columns, pd.MultiIndex):
    df.columns = [c[0] for c in df.columns]
  return df


def fetch_ohlcv_yf(symbol: str, timeframes: List[str]) -> Dict[str, pd.DataFrame]:
  cache = get_cache()
  result, hit = cache.get_or_compute(
    "ohlcv_yf",
    lambda: _fetch_ohlcv_yf_uncached(symbol, timeframes),
    symbol,
    tuple(timeframes),
  )
  if hit:
    print(f"[cache] HIT ohlcv_yf {symbol} tfs={timeframes}")
  return result


def _fetch_ohlcv_yf_uncached(symbol: str, timeframes: List[str]) -> Dict[str, pd.DataFrame]:
  out: Dict[str, pd.DataFrame] = {}
  for tf in timeframes:
    interval = YF_INTERVAL.get(tf, tf)
    period = YF_PERIOD.get(tf, "1y")
    df = yf.download(symbol, period=period, interval=interval, progress=False, auto_adjust=True)
    if df.empty:
      raise ValueError(f"No yfinance data for {symbol} {tf}")
    df = _unwrap_columns(df)
    df = df.rename(columns=str.title)
    if "Volume" not in df.columns:
      df["Volume"] = 0
    out[tf] = df[["Open", "High", "Low", "Close", "Volume"]].dropna()
    print(f"[fetch] yf {symbol} {tf}: {len(out[tf])} bars, last={out[tf]['Close'].iloc[-1]:.2f}")
  return out
