"""TradingView-style market structure — swing BOS / CHoCH (ICT-inspired, pandas-only)."""

from __future__ import annotations

from typing import Any, Dict, List, Optional, Tuple

import numpy as np
import pandas as pd


def _swing_points(high: pd.Series, low: pd.Series, left: int = 2, right: int = 2) -> Tuple[List[int], List[int]]:
  """Local swing high/low indices."""
  sh: List[int] = []
  sl: List[int] = []
  n = len(high)
  for i in range(left, n - right):
    h_win = high.iloc[i - left : i + right + 1]
    l_win = low.iloc[i - left : i + right + 1]
    if high.iloc[i] >= h_win.max():
      sh.append(i)
    if low.iloc[i] <= l_win.min():
      sl.append(i)
  return sh, sl


def detect_market_structure(df: pd.DataFrame, swing: int = 3) -> Dict[str, Any]:
  """
  Detect trend bias and recent structure events from swing highs/lows.
  BOS = break of structure (continuation); CHoCH = change of character (reversal hint).
  """
  if df is None or len(df) < swing * 4 + 10:
    return {"available": False, "reason": "insufficient_bars"}

  high = df["High"].astype(float)
  low = df["Low"].astype(float)
  close = df["Close"].astype(float)
  sh_idx, sl_idx = _swing_points(high, low, swing, swing)
  if len(sh_idx) < 2 or len(sl_idx) < 2:
    return {"available": False, "reason": "no_swings"}

  last_sh = sh_idx[-1]
  prev_sh = sh_idx[-2]
  last_sl = sl_idx[-1]
  prev_sl = sl_idx[-2]
  last_close = float(close.iloc[-1])
  last_high = float(high.iloc[last_sh])
  prev_high = float(high.iloc[prev_sh])
  last_low = float(low.iloc[last_sl])
  prev_low = float(low.iloc[prev_sl])

  trend = "neutral"
  if last_high > prev_high and last_low > prev_low:
    trend = "bullish"
  elif last_high < prev_high and last_low < prev_low:
    trend = "bearish"

  event = "none"
  bias = "neutral"
  if last_close > prev_high:
    event = "bos_bull" if trend == "bullish" else "choch_bull"
    bias = "bullish"
  elif last_close < prev_low:
    event = "bos_bear" if trend == "bearish" else "choch_bear"
    bias = "bearish"

  return {
    "available": True,
    "trend": trend,
    "event": event,
    "bias": bias,
    "last_swing_high": round(last_high, 6),
    "last_swing_low": round(last_low, 6),
    "close": round(last_close, 6),
    "choch": event.startswith("choch"),
    "bos": event.startswith("bos"),
  }


def score_market_structure(ms: dict, direction: str = "LONG") -> Dict[str, Any]:
  """Score 0–100 alignment with trade direction."""
  if not ms.get("available"):
    return {"score": 50, "aligned": False, "signals": []}
  is_long = direction.upper() in ("LONG", "BULL")
  score = 50
  signals: List[str] = []
  bias = ms.get("bias", "neutral")
  event = ms.get("event", "none")

  if is_long and bias == "bullish":
    score += 15
    signals.append(f"structure {event}")
  elif not is_long and bias == "bearish":
    score += 15
    signals.append(f"structure {event}")
  elif bias == "neutral":
    score += 0
  else:
    score -= 12
    signals.append(f"structure against ({event})")

  if ms.get("choch"):
    score += 5 if (is_long and "bull" in event) or (not is_long and "bear" in event) else -5
    signals.append("CHoCH")

  aligned = score >= 58
  return {"score": max(0, min(100, score)), "aligned": aligned, "signals": signals}
