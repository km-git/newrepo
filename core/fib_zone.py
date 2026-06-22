"""Tight Kill Zone clustering from Fibonacci levels."""

from __future__ import annotations

from typing import Dict, Tuple

import numpy as np
import pandas as pd

FIB_RATIOS = [0.236, 0.382, 0.5, 0.618, 0.786]


def compute_prior_decline_fibs(df: pd.DataFrame) -> Dict[str, float]:
  """Fib retracement levels from largest historical swing high to low."""
  highs = df["High"].values.astype(float)
  lows = df["Low"].values.astype(float)
  if len(highs) < 10:
    return {}
  # Largest swing: global high to subsequent low (or vice versa)
  hi_idx = int(np.argmax(highs))
  lo_idx = int(np.argmin(lows))
  if hi_idx < lo_idx:
    swing_high = highs[hi_idx]
    swing_low = lows[lo_idx]
  else:
    swing_high = highs[lo_idx]
    swing_low = lows[hi_idx]
  span = swing_high - swing_low
  if span <= 0:
    return {}
  return {f"fib_{r}": swing_high - span * r for r in FIB_RATIOS}


def compute_tight_kill_zone(
  c_target_100: float,
  c_target_161: float,
  prior_decline_fib_levels: Dict[str, float],
  current_price: float,
  max_width_pct: float = 2.0,
) -> Tuple[float, float]:
  candidates = [c_target_100, c_target_161] + list(prior_decline_fib_levels.values())
  best_cluster = None
  best_width = float("inf")

  for i in range(len(candidates)):
    for j in range(i + 1, len(candidates)):
      low = min(candidates[i], candidates[j])
      high = max(candidates[i], candidates[j])
      width_pct = (high - low) / current_price * 100
      if width_pct <= max_width_pct and (high - low) < best_width:
        best_width = high - low
        best_cluster = (low, high)

  if best_cluster is None:
    return (c_target_161 * 0.99, c_target_161 * 1.01)

  return (best_cluster[0] - 200, best_cluster[1] + 200)
