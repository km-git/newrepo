"""ATR(14) and median daily range."""

from __future__ import annotations

import numpy as np
import pandas as pd


def compute_atr14(df: pd.DataFrame, period: int = 14) -> float:
  high = df["High"].values.astype(float)
  low = df["Low"].values.astype(float)
  close = df["Close"].values.astype(float)
  n = len(close)
  if n < 2:
    return 0.0
  tr = np.zeros(n)
  tr[0] = high[0] - low[0]
  for i in range(1, n):
    tr[i] = max(high[i] - low[i], abs(high[i] - close[i - 1]), abs(low[i] - close[i - 1]))
  if n < period:
    return float(np.mean(tr))
  return float(np.mean(tr[-period:]))


def median_daily_range(df: pd.DataFrame) -> float:
  ranges = df["High"].values.astype(float) - df["Low"].values.astype(float)
  return float(np.median(ranges))
