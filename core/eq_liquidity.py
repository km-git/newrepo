"""Equal highs/lows (EQH/EQL) liquidity detection and sweep — ICT-style."""

from __future__ import annotations

from typing import List, Optional, Tuple

import numpy as np
import pandas as pd


def _pivot_indices(series: pd.Series, left: int, right: int, mode: str) -> List[int]:
  vals = series.astype(float).values
  n = len(vals)
  out: List[int] = []
  for i in range(left, n - right):
    window = vals[i - left : i + right + 1]
    if mode == "high" and vals[i] == np.nanmax(window):
      out.append(i)
    elif mode == "low" and vals[i] == np.nanmin(window):
      out.append(i)
  return out


def detect_equal_levels(
  df: pd.DataFrame,
  lookback: int = 80,
  pivot_len: int = 5,
  tolerance_pct: float = 0.0015,
  min_touches: int = 2,
) -> dict:
  """
  Cluster pivot highs into equal highs (EQH) and pivot lows into equal lows (EQL).
  """
  if df is None or len(df) < lookback:
    return {"status": "insufficient_data"}

  window = df.tail(lookback)
  high = window["High"].astype(float)
  low = window["Low"].astype(float)
  price = float(df["Close"].iloc[-1])

  ph = _pivot_indices(high, pivot_len, pivot_len, "high")
  pl = _pivot_indices(low, pivot_len, pivot_len, "low")

  def _cluster(levels: List[Tuple[int, float]]) -> List[dict]:
    if len(levels) < min_touches:
      return []
    clusters: List[dict] = []
    used = set()
    for i, (idx_i, lvl_i) in enumerate(levels):
      if i in used:
        continue
      group = [(idx_i, lvl_i)]
      for j, (idx_j, lvl_j) in enumerate(levels):
        if j <= i or j in used:
          continue
        tol = max(lvl_i, lvl_j) * tolerance_pct
        if abs(lvl_i - lvl_j) <= tol:
          group.append((idx_j, lvl_j))
          used.add(j)
      if len(group) >= min_touches:
        used.add(i)
        avg = float(np.mean([g[1] for g in group]))
        clusters.append({
          "level": round(avg, 6),
          "touches": len(group),
          "last_idx": max(g[0] for g in group),
        })
    return sorted(clusters, key=lambda c: c["last_idx"], reverse=True)

  ph_levels = [(i, float(high.iloc[i])) for i in ph]
  pl_levels = [(i, float(low.iloc[i])) for i in pl]
  eq_highs = _cluster(ph_levels)
  eq_lows = _cluster(pl_levels)

  return {
    "status": "ok",
    "eq_highs": eq_highs,
    "eq_lows": eq_lows,
    "price": price,
    "has_eqh": bool(eq_highs),
    "has_eql": bool(eq_lows),
  }


def detect_eq_sweep(
  df: pd.DataFrame,
  direction: str,
  lookback: int = 30,
  pivot_len: int = 5,
) -> Optional[dict]:
  """
  ICT sweep: wick beyond EQ level + close back inside.
  LONG: sweep below EQL (sell-side liquidity) then reclaim.
  SHORT: sweep above EQH (buy-side liquidity) then reject.
  """
  if df is None or len(df) < lookback + 10:
    return None

  eq = detect_equal_levels(df, lookback=lookback + 20, pivot_len=pivot_len)
  if eq.get("status") != "ok":
    return None

  is_long = direction in ("LONG", "BULL")
  tail = df.tail(lookback)
  close = tail["Close"].astype(float)
  high = tail["High"].astype(float)
  low = tail["Low"].astype(float)

  levels = eq["eq_lows"] if is_long else eq["eq_highs"]
  if not levels:
    return None

  for lvl_info in levels:
    level = float(lvl_info["level"])
    for i in range(len(tail) - 1, max(0, len(tail) - 20), -1):
      if is_long:
        swept = float(low.iloc[i]) < level and float(close.iloc[i]) > level
        tag = "liquidity sweep (EQL)"
      else:
        swept = float(high.iloc[i]) > level and float(close.iloc[i]) < level
        tag = "liquidity sweep (EQH)"
      if swept:
        return {
          "level": level,
          "swept_idx": i,
          "type": "eql" if is_long else "eqh",
          "tag": tag,
          "touches": lvl_info.get("touches", 2),
        }
  return None
