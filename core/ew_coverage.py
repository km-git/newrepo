"""Adaptive monowave extraction — maximize EW coverage on thin data."""

from __future__ import annotations

from typing import List, Tuple

import pandas as pd

from core.monowaves import compute_skip, extract_monowaves, extract_monowaves_cached
from core.atr import compute_atr14, median_daily_range


def extract_monowaves_adaptive(
  df: pd.DataFrame,
  cache_tag: str = "",
  min_waves: int = 3,
) -> Tuple[List[dict], int]:
  """
  Extract monowaves with decreasing skip until enough structure is found.
  Returns (monowaves, skip_used).
  """
  if df is None or len(df) < 10:
    return [], 3

  atr = compute_atr14(df)
  med = median_daily_range(df)
  initial = compute_skip(atr, med)
  best: List[dict] = []
  best_skip = initial

  for skip in range(initial, 2, -1):
    if cache_tag:
      mws = extract_monowaves_cached(df, skip, cache_tag=f"{cache_tag}_s{skip}")
    else:
      mws = extract_monowaves(df, skip)
    if len(mws) >= 5:
      return mws, skip
    if len(mws) > len(best):
      best, best_skip = mws, skip

  if len(best) < min_waves and initial > 3:
    mws = extract_monowaves(df, 3)
    if len(mws) > len(best):
      best, best_skip = mws, 3

  return best, best_skip


def build_adaptive_pivots(
  symbol: str,
  data: dict,
  tfs: List[str],
) -> dict:
  """Build adaptive pivot dict for every requested timeframe."""
  adaptive: dict = {}
  for tf in tfs:
    if tf not in data or data[tf] is None or len(data[tf]) < 5:
      adaptive[tf] = {
        "skip": 0,
        "monowaves": [],
        "atr_14": 0.0,
        "bars": 0,
        "status": "no_data",
      }
      continue
    df = data[tf]
    atr = compute_atr14(df)
    mws, skip = extract_monowaves_adaptive(df, cache_tag=f"{symbol}_{tf}")
    adaptive[tf] = {
      "skip": skip,
      "monowaves": mws,
      "atr_14": atr,
      "bars": len(df),
      "status": "ok" if mws else "no_monowaves",
    }
  return adaptive
