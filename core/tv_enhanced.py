"""
TradingView-parity enhanced indicators via QuanTAlib (mihakralj/QuanTAlib).

Adds dynamics, divergence, and momentum layers missing from the thin RSI/EMA stack.
Falls back to pandas if quantalib is unavailable.
"""

from __future__ import annotations

from typing import List, Optional, Tuple

import numpy as np
import pandas as pd

try:
  import quantalib as qtl
  _HAS_QTL = True
except ImportError:
  _HAS_QTL = False


def _arr(series: pd.Series) -> np.ndarray:
  return series.astype(float).values


def _last_valid(arr: np.ndarray, default: float = 0.0) -> float:
  if arr is None or len(arr) == 0:
    return default
  for v in reversed(arr):
    if v is not None and np.isfinite(v):
      return float(v)
  return default


def compute_enhanced_indicators(df: pd.DataFrame) -> dict:
  """ADX, SuperTrend, Williams %R, Stochastic, momentum z-score."""
  if df is None or len(df) < 30:
    return {"status": "insufficient_data", "score": 0, "tags": []}

  close = df["Close"].astype(float)
  high = df["High"].astype(float)
  low = df["Low"].astype(float)
  c = _arr(close)
  h = _arr(high)
  l = _arr(low)

  out: dict = {"status": "ok", "tags": [], "source": "quantalib" if _HAS_QTL else "pandas"}

  if _HAS_QTL:
    try:
      adx = qtl.adx(h, l, c, period=14)
      out["adx"] = round(_last_valid(adx), 2)
      o = _arr(df["Open"].astype(float)) if "Open" in df.columns else c
      vol = _arr(df["Volume"].astype(float)) if "Volume" in df.columns else np.ones_like(c)
      st = qtl.supertrend(o, h, l, c, vol, period=10, multiplier=3.0)
      out["supertrend"] = round(_last_valid(st), 6)
      out["price_above_supertrend"] = float(close.iloc[-1]) > out["supertrend"]
      out["willr"] = round(_last_valid(qtl.willr(h, l, c, period=14)), 2)
      stoch_k = qtl.stoch(h, l, c, kLength=14, dPeriod=3)
      out["stoch_k"] = round(_last_valid(stoch_k), 2)
      mom = c[-20:]
      if len(mom) >= 10:
        z = (mom[-1] - np.mean(mom)) / (np.std(mom) + 1e-9)
        out["momentum_z"] = round(float(z), 3)
      else:
        out["momentum_z"] = 0.0
    except Exception as e:
      out["status"] = "fallback"
      out["error"] = str(e)
  else:
    out["source"] = "pandas"
    delta = close.diff()
    gain = delta.clip(lower=0).rolling(14).mean()
    loss = (-delta.clip(upper=0)).rolling(14).mean()
    rs = gain / loss.replace(0, np.nan)
    rsi = 100 - (100 / (1 + rs))
    out["rsi14"] = round(float(rsi.iloc[-1]), 2) if len(rsi) else 50.0
    out["willr"] = round(float(
      (high.rolling(14).max().iloc[-1] - close.iloc[-1])
      / max(high.rolling(14).max().iloc[-1] - low.rolling(14).min().iloc[-1], 1e-9) * -100
    ), 2)
    out["adx"] = 20.0
    out["momentum_z"] = 0.0
    out["price_above_supertrend"] = float(close.iloc[-1]) > float(close.rolling(20).mean().iloc[-1])

  return out


def detect_oscillator_divergence(
  df: pd.DataFrame,
  lookback: int = 20,
) -> Optional[str]:
  """Regular divergence on price vs RSI (capital41 / Quant-Edge style)."""
  if df is None or len(df) < lookback + 15:
    return None
  close = df["Close"].astype(float)
  segment = close.iloc[-lookback:]
  rsi_vals = []
  for i in range(lookback):
    sub = close.iloc[: len(close) - lookback + i + 1]
    if len(sub) < 15:
      continue
    if _HAS_QTL:
      rsi_vals.append(_last_valid(qtl.rsi(_arr(sub), period=14), 50))
    else:
      delta = sub.diff()
      gain = delta.clip(lower=0).rolling(14).mean()
      loss = (-delta.clip(upper=0)).rolling(14).mean()
      rs = gain / loss.replace(0, np.nan)
      rsi_vals.append(float((100 - (100 / (1 + rs))).iloc[-1]))
  if len(rsi_vals) < 5:
    return None
  p0, p1 = float(segment.iloc[0]), float(segment.iloc[-1])
  r0, r1 = rsi_vals[0], rsi_vals[-1]
  if p1 < p0 and r1 > r0:
    return "bullish_divergence"
  if p1 > p0 and r1 < r0:
    return "bearish_divergence"
  return None


def score_enhanced_confluence(enhanced: dict, direction: str, divergence: Optional[str]) -> Tuple[int, List[str]]:
  """Score 0-40 for TV-enhanced layer."""
  if enhanced.get("status") not in ("ok", "fallback"):
    return 0, []
  is_long = direction in ("LONG", "BULL")
  score = 0
  tags: List[str] = []

  adx = enhanced.get("adx", 0)
  if adx >= 25:
    score += 8
    tags.append(f"ADX {adx:.0f} trend strong")

  if is_long and enhanced.get("price_above_supertrend"):
    score += 10
    tags.append("above SuperTrend")
  elif not is_long and not enhanced.get("price_above_supertrend", True):
    score += 10
    tags.append("below SuperTrend")

  willr = enhanced.get("willr", -50)
  if is_long and willr < -80:
    score += 8
    tags.append("Williams %R oversold")
  elif not is_long and willr > -20:
    score += 8
    tags.append("Williams %R overbought")

  mz = enhanced.get("momentum_z", 0)
  if is_long and mz > 1.0:
    score += 6
    tags.append(f"momentum z={mz:.1f}")
  elif not is_long and mz < -1.0:
    score += 6
    tags.append(f"momentum z={mz:.1f}")

  if divergence == "bullish_divergence" and is_long:
    score += 12
    tags.append("RSI bullish divergence")
  elif divergence == "bearish_divergence" and not is_long:
    score += 12
    tags.append("RSI bearish divergence")

  return min(40, score), tags
