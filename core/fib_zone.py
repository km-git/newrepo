"""Direction-aware C-wave targets and price-proximate kill zones."""

from __future__ import annotations

from typing import Dict, Tuple

import numpy as np
import pandas as pd

FIB_RATIOS = [0.236, 0.382, 0.5, 0.618, 0.786]


def compute_prior_decline_fibs(df: pd.DataFrame) -> Dict[str, float]:
  """
  Retrace fib levels from the most recent swing leg (temporal order preserved).
  Decline (high then low): retrace upward from swing low.
  Rally (low then high): retrace downward from swing high.
  """
  highs = df["High"].values.astype(float)
  lows = df["Low"].values.astype(float)
  if len(highs) < 10:
    return {}
  hi_idx = int(np.argmax(highs))
  lo_idx = int(np.argmin(lows))
  if hi_idx < lo_idx:
    swing_high, swing_low = float(highs[hi_idx]), float(lows[lo_idx])
    span = swing_high - swing_low
    if span <= 0:
      return {}
    return {f"fib_{r}": swing_low + span * r for r in FIB_RATIOS}
  swing_low, swing_high = float(lows[lo_idx]), float(highs[hi_idx])
  span = swing_high - swing_low
  if span <= 0:
    return {}
  return {f"fib_{r}": swing_high - span * r for r in FIB_RATIOS}


def compute_c_targets(wave_a: dict, b_end: float, bias: str, state: str) -> dict:
  """
  Direction-aware Elliott C-wave extension from wave A magnitude.
  Down A + bullish_reversal → C up from B; Up A + bearish → C down from B.
  """
  mag = abs(wave_a["end"] - wave_a["start"])
  wtype = wave_a.get("type", "Down")
  b = bias.lower()

  bullish_rev = "bullish_reversal" in b or state == "bullish_impulse"
  bearish_rev = "bearish_reversal" in b or state == "bearish_impulse"

  if bullish_rev or (not bearish_rev and wtype == "Down"):
    t100 = b_end + mag
    t161 = b_end + mag * 1.618
    direction = "up"
  elif bearish_rev or wtype == "Up":
    t100 = b_end - mag
    t161 = b_end - mag * 1.618
    direction = "down"
  else:
    if wtype == "Down":
      t100 = b_end + mag * 0.618
      t161 = b_end + mag
      direction = "up_retrace"
    else:
      t100 = b_end - mag * 0.618
      t161 = b_end - mag
      direction = "down_retrace"

  return {
    "c_target_100": t100,
    "c_target_161": t161,
    "c_direction": direction,
    "wave_a_mag": mag,
    "b_end": b_end,
  }


def compute_tight_kill_zone(
  c_target_100: float,
  c_target_161: float,
  prior_decline_fib_levels: Dict[str, float],
  current_price: float,
  max_width_pct: float = 2.5,
  max_distance_pct: float = 15.0,
) -> Tuple[float, float, dict]:
  """
  Cluster Fib levels near current price (not arbitrary distant C targets).
  Returns (low, high, metadata).
  """
  all_candidates = {
    "c_100": c_target_100,
    "c_161": c_target_161,
    **prior_decline_fib_levels,
  }

  def _dist_pct(level: float) -> float:
    return abs(level - current_price) / current_price * 100

  near = {k: v for k, v in all_candidates.items() if _dist_pct(v) <= max_distance_pct}
  if len(near) < 2:
    ranked = sorted(all_candidates.items(), key=lambda kv: _dist_pct(kv[1]))
    near = dict(ranked[: min(5, len(ranked))])

  values = list(near.values())
  best_cluster = None
  best_width = float("inf")
  best_keys: Tuple[str, str] = ("", "")

  keys = list(near.keys())
  for i in range(len(values)):
    for j in range(i + 1, len(values)):
      low = min(values[i], values[j])
      high = max(values[i], values[j])
      width_pct = (high - low) / current_price * 100
      if width_pct <= max_width_pct and (high - low) < best_width:
        best_width = high - low
        best_cluster = (low, high)
        best_keys = (keys[i], keys[j])

  if best_cluster is None:
    # Anchor on nearest single fib to current price
    nearest_k, nearest_v = min(near.items(), key=lambda kv: _dist_pct(kv[1]))
    band = current_price * 0.01
    meta = {"cluster": [nearest_k], "anchor": nearest_k, "fallback": True}
    return nearest_v - band, nearest_v + band, meta

  pad = current_price * 0.005
  meta = {
    "cluster": list(best_keys),
    "distance_pct": round(_dist_pct((best_cluster[0] + best_cluster[1]) / 2), 2),
    "fallback": False,
  }
  return best_cluster[0] - pad, best_cluster[1] + pad, meta
