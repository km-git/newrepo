"""Adaptive MonoWave extraction."""

from __future__ import annotations

from typing import List

import numpy as np
import pandas as pd

from cache.disk_cache import get_cache
from cache.dedup import dedup_monowaves
from core.atr import compute_atr14, median_daily_range


def compute_skip(atr_14: float, median_range: float) -> int:
  denom = median_range * 0.10
  if denom <= 0:
    return 3
  return max(3, int(atr_14 / denom))


def extract_monowaves(df: pd.DataFrame, skip: int) -> List[dict]:
  highs = df["High"].values.astype(float)
  lows = df["Low"].values.astype(float)
  dates = df.index
  n = len(highs)
  mws: List[dict] = []
  idx = 0
  slope = (highs[5] + lows[5]) / 2 - (highs[0] + lows[0]) / 2 if n > 5 else 0
  nxt = "Up" if slope > 0 else "Down"
  iters = 0
  while idx < n - skip and iters < n:
    iters += 1
    if nxt == "Up":
      end = idx + skip
      for j in range(idx + skip, n):
        if highs[j] > highs[end]:
          end = j
        if j > idx + skip and lows[j] < lows[idx]:
          break
      if end <= idx:
        idx += 1
        continue
      mws.append(
        {
          "type": "Up",
          "idx_start": idx,
          "idx_end": end,
          "price_start": float(lows[idx : end + 1].min()),
          "price_end": float(highs[end]),
          "date_start": str(dates[idx].date()) if hasattr(dates[idx], "date") else str(dates[idx]),
          "date_end": str(dates[end].date()) if hasattr(dates[end], "date") else str(dates[end]),
        }
      )
      idx = end
      nxt = "Down"
    else:
      end = idx + skip
      for j in range(idx + skip, n):
        if lows[j] < lows[end]:
          end = j
        if j > idx + skip and highs[j] > highs[idx]:
          break
      if end <= idx:
        idx += 1
        continue
      mws.append(
        {
          "type": "Down",
          "idx_start": idx,
          "idx_end": end,
          "price_start": float(highs[idx : end + 1].max()),
          "price_end": float(lows[end]),
          "date_start": str(dates[idx].date()) if hasattr(dates[idx], "date") else str(dates[idx]),
          "date_end": str(dates[end].date()) if hasattr(dates[end], "date") else str(dates[end]),
        }
      )
      idx = end
      nxt = "Up"
  return dedup_monowaves(mws)


def extract_monowaves_cached(df: pd.DataFrame, skip: int, cache_tag: str = "") -> List[dict]:
  cache = get_cache()
  last_close = float(df["Close"].iloc[-1])
  last_ts = str(df.index[-1])
  result, hit = cache.get_or_compute(
    "monowaves",
    lambda: extract_monowaves(df, skip),
    cache_tag,
    skip,
    len(df),
    last_ts,
    round(last_close, 2),
  )
  if hit:
    print(f"[cache] HIT monowaves tag={cache_tag} skip={skip}")
  return result


def adaptive_skip_for_df(df: pd.DataFrame) -> int:
  atr = compute_atr14(df)
  med = median_daily_range(df)
  skip = compute_skip(atr, med)
  print(f"[monowaves] ATR14={atr:.2f} median_range={med:.2f} skip={skip}")
  return skip
