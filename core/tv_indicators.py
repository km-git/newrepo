"""
TradingView-style open-source indicator ports (pure pandas).

Common OSS patterns: Supertrend (ATR bands), Bollinger %B, ADX trend strength.
Reference implementations align with widely published Pine Script logic.
"""

from __future__ import annotations

from typing import Any, Dict, Optional

import numpy as np
import pandas as pd


def _true_range(high: pd.Series, low: pd.Series, close: pd.Series) -> pd.Series:
  prev = close.shift(1)
  return pd.concat(
    [(high - low).abs(), (high - prev).abs(), (low - prev).abs()],
    axis=1,
  ).max(axis=1)


def atr_series(df: pd.DataFrame, period: int = 14) -> pd.Series:
  tr = _true_range(df["High"].astype(float), df["Low"].astype(float), df["Close"].astype(float))
  return tr.ewm(alpha=1 / period, adjust=False).mean()


def supertrend(
  df: pd.DataFrame,
  period: int = 10,
  multiplier: float = 3.0,
) -> Dict[str, Any]:
  """
  Supertrend direction: +1 bullish, -1 bearish.
  """
  if df is None or len(df) < period + 2:
    return {"available": False, "direction": 0, "value": None, "signal": "neutral"}

  hl2 = (df["High"].astype(float) + df["Low"].astype(float)) / 2
  atr = atr_series(df, period)
  upper = hl2 + multiplier * atr
  lower = hl2 - multiplier * atr

  close = df["Close"].astype(float)
  st = pd.Series(index=df.index, dtype=float)
  direction = pd.Series(index=df.index, dtype=int)

  st.iloc[0] = upper.iloc[0]
  direction.iloc[0] = 1

  for i in range(1, len(df)):
    if close.iloc[i - 1] <= st.iloc[i - 1]:
      st.iloc[i] = min(upper.iloc[i], st.iloc[i - 1]) if not np.isnan(st.iloc[i - 1]) else upper.iloc[i]
    else:
      st.iloc[i] = max(lower.iloc[i], st.iloc[i - 1]) if not np.isnan(st.iloc[i - 1]) else lower.iloc[i]

    if close.iloc[i] > st.iloc[i]:
      direction.iloc[i] = 1
    elif close.iloc[i] < st.iloc[i]:
      direction.iloc[i] = -1
    else:
      direction.iloc[i] = direction.iloc[i - 1]

  d = int(direction.iloc[-1])
  val = float(st.iloc[-1])
  signal = "bullish" if d > 0 else "bearish" if d < 0 else "neutral"
  flipped = direction.iloc[-1] != direction.iloc[-2] if len(direction) > 1 else False
  return {
    "available": True,
    "direction": d,
    "value": round(val, 8),
    "signal": signal,
    "flip": bool(flipped),
  }


def bollinger_bands(
  df: pd.DataFrame,
  period: int = 20,
  std_mult: float = 2.0,
) -> Dict[str, Any]:
  if df is None or len(df) < period:
    return {"available": False, "pct_b": 0.5, "signal": "neutral"}

  close = df["Close"].astype(float)
  mid = close.rolling(period).mean()
  std = close.rolling(period).std()
  upper = mid + std_mult * std
  lower = mid - std_mult * std
  width = (upper - lower).replace(0, np.nan)
  pct_b = (close - lower) / width
  pb = float(pct_b.iloc[-1]) if np.isfinite(pct_b.iloc[-1]) else 0.5
  bw = float((width.iloc[-1] / mid.iloc[-1] * 100)) if mid.iloc[-1] else 0

  if pb <= 0.05:
    signal = "oversold"
  elif pb >= 0.95:
    signal = "overbought"
  elif pb < 0.35:
    signal = "lower_band"
  elif pb > 0.65:
    signal = "upper_band"
  else:
    signal = "mid_range"

  return {
    "available": True,
    "pct_b": round(pb, 4),
    "bandwidth_pct": round(bw, 3),
    "signal": signal,
    "squeeze": bw < 4.0,
  }


def adx(
  df: pd.DataFrame,
  period: int = 14,
) -> Dict[str, Any]:
  """ADX trend strength (0–100); +DI / -DI for direction."""
  if df is None or len(df) < period * 2:
    return {"available": False, "adx": 0, "trend": "weak", "di_bias": "neutral"}

  high = df["High"].astype(float)
  low = df["Low"].astype(float)
  close = df["Close"].astype(float)

  up = high.diff()
  down = -low.diff()
  plus_dm = np.where((up > down) & (up > 0), up, 0.0)
  minus_dm = np.where((down > up) & (down > 0), down, 0.0)

  tr = _true_range(high, low, close)
  atr = tr.ewm(alpha=1 / period, adjust=False).mean()
  plus_di = 100 * pd.Series(plus_dm, index=df.index).ewm(alpha=1 / period, adjust=False).mean() / atr
  minus_di = 100 * pd.Series(minus_dm, index=df.index).ewm(alpha=1 / period, adjust=False).mean() / atr

  dx = (abs(plus_di - minus_di) / (plus_di + minus_di).replace(0, np.nan)) * 100
  adx_val = dx.ewm(alpha=1 / period, adjust=False).mean()
  a = float(adx_val.iloc[-1]) if np.isfinite(adx_val.iloc[-1]) else 0
  pdi = float(plus_di.iloc[-1])
  mdi = float(minus_di.iloc[-1])

  if a >= 25:
    trend = "strong"
  elif a >= 18:
    trend = "moderate"
  else:
    trend = "weak"

  di_bias = "bull" if pdi > mdi else "bear" if mdi > pdi else "neutral"
  return {
    "available": True,
    "adx": round(a, 2),
    "plus_di": round(pdi, 2),
    "minus_di": round(mdi, 2),
    "trend": trend,
    "di_bias": di_bias,
  }


def compute_tv_signals(df: pd.DataFrame) -> Dict[str, Any]:
  """Bundle TV-style signals for one OHLCV frame."""
  st = supertrend(df)
  bb = bollinger_bands(df)
  ax = adx(df)
  atr = atr_series(df) if df is not None and len(df) >= 15 else pd.Series(dtype=float)
  atr_pct = 0.0
  if len(atr) and df is not None:
    price = float(df["Close"].iloc[-1])
    if price > 0:
      atr_pct = float(atr.iloc[-1] / price * 100)

  return {
    "supertrend": st,
    "bollinger": bb,
    "adx": ax,
    "atr_pct": round(atr_pct, 3),
  }


def score_tv_confluence(
  df: pd.DataFrame,
  direction: str,
) -> Dict[str, Any]:
  """
  Score 0–100: alignment of TV OSS signals with trade direction.
  Helps filter false probe entries and size down choppy regimes.
  """
  signals = compute_tv_signals(df)
  is_long = direction.upper() in ("LONG", "BULL")
  score = 0
  notes = []

  st = signals["supertrend"]
  if st.get("available"):
    if (is_long and st["direction"] > 0) or (not is_long and st["direction"] < 0):
      score += 30
      notes.append(f"supertrend {st['signal']}")
    elif st["direction"] != 0:
      score -= 15
      notes.append(f"supertrend opposes ({st['signal']})")
    if st.get("flip"):
      notes.append("supertrend flip (caution)")

  bb = signals["bollinger"]
  if bb.get("available"):
    if is_long and bb["pct_b"] < 0.35:
      score += 20
      notes.append(f"BB %B {bb['pct_b']:.2f} favorable long")
    elif not is_long and bb["pct_b"] > 0.65:
      score += 20
      notes.append(f"BB %B {bb['pct_b']:.2f} favorable short")
    elif is_long and bb["signal"] == "overbought":
      score -= 10
      notes.append("BB overbought vs long")
    elif not is_long and bb["signal"] == "oversold":
      score -= 10
      notes.append("BB oversold vs short")
    if bb.get("squeeze"):
      score -= 5
      notes.append("BB squeeze (reduce size)")

  ax = signals["adx"]
  if ax.get("available"):
    if ax["trend"] == "strong":
      if (is_long and ax["di_bias"] == "bull") or (not is_long and ax["di_bias"] == "bear"):
        score += 25
        notes.append(f"ADX {ax['adx']:.0f} trend aligned")
      else:
        score += 5
        notes.append(f"ADX strong but DI mixed")
    elif ax["trend"] == "weak":
      score -= 10
      notes.append(f"ADX {ax['adx']:.0f} choppy — tighten risk")

  # Volatility regime via ATR%
  atr_pct = signals.get("atr_pct", 0)
  if atr_pct > 5:
    notes.append(f"high vol ATR%={atr_pct}")
  elif atr_pct < 1:
    notes.append(f"low vol ATR%={atr_pct}")

  score = max(0, min(100, score + 25))  # baseline 25 when data exists
  aligned = score >= 55
  return {
    "score": score,
    "aligned": aligned,
    "signals": notes,
    "raw": signals,
    "atr_pct": atr_pct,
  }
