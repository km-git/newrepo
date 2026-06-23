"""LuxAlgo-style MSB (market structure break) z-score momentum filter."""

from __future__ import annotations

from typing import Optional, Tuple

import numpy as np
import pandas as pd


DEFAULT_Z_THRESHOLD = 1.5


def _break_momentum_series(df: pd.DataFrame, period: int = 20) -> pd.Series:
  """Per-bar break momentum: signed close-to-open body normalized by rolling std."""
  close = df["Close"].astype(float)
  open_ = df["Open"].astype(float) if "Open" in df.columns else close.shift(1).fillna(close)
  body = close - open_
  std = body.rolling(period, min_periods=max(5, period // 2)).std().replace(0, np.nan)
  return body / std


def msb_z_at_bar(df: pd.DataFrame, bar_idx: int, period: int = 20) -> float:
  """Z-score of break momentum at a specific bar index."""
  mom = _break_momentum_series(df, period)
  if bar_idx < 0 or bar_idx >= len(mom):
    return 0.0
  val = mom.iloc[bar_idx]
  return float(val) if pd.notna(val) else 0.0


def find_last_structure_break(
  df: pd.DataFrame,
  direction: str,
  pivot_len: int = 5,
  lookback: int = 60,
) -> Tuple[Optional[int], Optional[str]]:
  """Find most recent BOS/CHoCH bar index in direction."""
  if df is None or len(df) < lookback:
    return None, None

  is_long = direction in ("LONG", "BULL")
  tail = df.tail(lookback)
  high = tail["High"].astype(float)
  low = tail["Low"].astype(float)
  close = tail["Close"].astype(float)
  n = len(tail)

  swing_highs = []
  swing_lows = []
  for i in range(pivot_len, n - pivot_len):
    if high.iloc[i] == high.iloc[i - pivot_len : i + pivot_len + 1].max():
      swing_highs.append((i, float(high.iloc[i])))
    if low.iloc[i] == low.iloc[i - pivot_len : i + pivot_len + 1].min():
      swing_lows.append((i, float(low.iloc[i])))

  trend = 0
  last_idx = None
  last_event = None
  for i in range(1, n):
    c0, c1 = float(close.iloc[i]), float(close.iloc[i - 1])
    for _, sh in reversed(swing_highs):
      if _ < i and c0 > sh and c1 <= sh:
        last_event = "choch_bull" if trend == -1 else "bos_bull"
        trend = 1
        last_idx = i
        break
    for _, sl in reversed(swing_lows):
      if _ < i and c0 < sl and c1 >= sl:
        last_event = "choch_bear" if trend == 1 else "bos_bear"
        trend = -1
        last_idx = i
        break

  if last_idx is None:
    return None, None
  if is_long and last_event not in ("bos_bull", "choch_bull"):
    return None, None
  if not is_long and last_event not in ("bos_bear", "choch_bear"):
    return None, None
  abs_idx = len(df) - n + last_idx
  return abs_idx, last_event


def validate_msb_zscore(
  df: pd.DataFrame,
  direction: str,
  threshold: float = DEFAULT_Z_THRESHOLD,
  period: int = 20,
) -> dict:
  """
  LuxAlgo MSB filter: structure break must have conviction (|z| >= threshold).
  """
  if df is None or len(df) < period + 10:
    return {"status": "insufficient_data", "pass": False, "z": 0.0}

  bar_idx, event = find_last_structure_break(df, direction)
  if bar_idx is None:
    return {"status": "no_break", "pass": False, "z": 0.0, "event": None}

  z = msb_z_at_bar(df, bar_idx, period)
  is_long = direction in ("LONG", "BULL")
  directional_z = z if is_long else -z
  passed = directional_z >= threshold

  return {
    "status": "ok",
    "pass": passed,
    "z": round(z, 3),
    "directional_z": round(directional_z, 3),
    "threshold": threshold,
    "event": event,
    "bar_idx": bar_idx,
    "tag": "MSB z-score pass" if passed else "MSB z-score weak",
  }


MSB_PASS_TOKEN = "MSB z-score pass"


def msb_blocks_entry(msb: Optional[dict]) -> bool:
  """
  Hard block MSB z-score pass from entry_signal.
  Ledger: pass token ~11% WR (anti-predictive); weak is also poor but pass is worse.
  """
  if not msb:
    return False
  return msb.get("status") == "ok" and bool(msb.get("pass"))


def msb_allows_entry(msb: Optional[dict]) -> bool:
  """True when MSB filter does not veto SMC entry."""
  return not msb_blocks_entry(msb)
