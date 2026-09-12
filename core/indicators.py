"""Technical indicators for execution confluence (pure pandas)."""

from __future__ import annotations

from typing import Any, Dict, List

import numpy as np
import pandas as pd


def _ema(series: pd.Series, span: int) -> pd.Series:
  return series.ewm(span=span, adjust=False).mean()


def rsi14(close: pd.Series) -> float:
  if len(close) < 15:
    return 50.0
  delta = close.diff()
  gain = delta.clip(lower=0).rolling(14).mean()
  loss = (-delta.clip(upper=0)).rolling(14).mean()
  rs = gain / loss.replace(0, np.nan)
  val = 100 - (100 / (1 + rs))
  return float(val.iloc[-1]) if not np.isnan(val.iloc[-1]) else 50.0


def macd_hist(close: pd.Series) -> tuple[float, float]:
  """Returns (histogram, histogram_delta vs prior bar)."""
  if len(close) < 30:
    return 0.0, 0.0
  ema12 = _ema(close, 12)
  ema26 = _ema(close, 26)
  macd = ema12 - ema26
  signal = _ema(macd, 9)
  hist = macd - signal
  h = float(hist.iloc[-1])
  prev = float(hist.iloc[-2]) if len(hist) > 1 else h
  return h, h - prev


def volume_ratio(df: pd.DataFrame, lookback: int = 20) -> float:
  if "Volume" not in df.columns or len(df) < lookback + 1:
    return 1.0
  vol = df["Volume"].astype(float)
  avg = vol.iloc[-lookback - 1 : -1].mean()
  if avg <= 0:
    return 1.0
  return float(vol.iloc[-1] / avg)


def zone_proximity_pct(price: float, zone_low: float, zone_high: float) -> float:
  """0 = inside zone, higher = farther from zone."""
  if zone_low > zone_high:
    zone_low, zone_high = zone_high, zone_low
  if zone_low <= price <= zone_high:
    return 0.0
  if price < zone_low:
    return (zone_low - price) / price * 100
  return (price - zone_high) / price * 100


def compute_raw_indicators(df: pd.DataFrame) -> dict:
  close = df["Close"].astype(float)
  price = float(close.iloc[-1])
  ema20 = float(_ema(close, 20).iloc[-1]) if len(close) >= 20 else price
  ema50 = float(_ema(close, 50).iloc[-1]) if len(close) >= 50 else price
  hist, hist_delta = macd_hist(close)
  return {
    "price": price,
    "rsi14": round(rsi14(close), 2),
    "ema20": round(ema20, 6),
    "ema50": round(ema50, 6),
    "macd_hist": round(hist, 6),
    "macd_hist_delta": round(hist_delta, 6),
    "volume_ratio": round(volume_ratio(df), 2),
    "above_ema20": price > ema20,
    "above_ema50": price > ema50,
  }


def collect_indicator_signals(
  raw: dict,
  direction: str,
  zdist: float,
) -> List[tuple[str, int]]:
  """Return (calibration_token, default_points) for active indicator signals."""
  pairs: List[tuple[str, int]] = []
  is_long = direction in ("LONG", "BULL")

  if zdist == 0:
    pairs.append(("in kill zone", 25))
  elif zdist < 1.5:
    pairs.append(("near zone", 18))
  elif zdist < 3.0:
    pairs.append(("approaching zone", 10))

  rsi = raw["rsi14"]
  if is_long:
    if 35 <= rsi <= 55:
      pairs.append(("RSI bullish reset", 20))
    elif 55 < rsi <= 65:
      pairs.append(("RSI momentum intact", 12))
    elif rsi < 35:
      pairs.append(("RSI oversold bounce", 15))
  else:
    if 45 <= rsi <= 65:
      pairs.append(("RSI bearish reset", 20))
    elif 35 <= rsi < 45:
      pairs.append(("RSI weakness intact", 12))
    elif rsi > 65:
      pairs.append(("RSI overbought fade", 15))

  if is_long:
    if raw["above_ema20"] and raw["above_ema50"]:
      pairs.append(("above EMA20/50", 20))
    elif raw["above_ema20"]:
      pairs.append(("above EMA20", 12))
    elif raw["price"] > raw["ema20"] * 0.995:
      pairs.append(("EMA20 support", 8))
  else:
    if not raw["above_ema20"] and not raw["above_ema50"]:
      pairs.append(("below EMA20/50", 20))
    elif not raw["above_ema20"]:
      pairs.append(("below EMA20", 12))
    elif raw["price"] < raw["ema20"] * 1.005:
      pairs.append(("EMA20 resistance", 8))

  if is_long and raw["macd_hist_delta"] > 0:
    pairs.append(("MACD rising", 20))
  elif not is_long and raw["macd_hist_delta"] < 0:
    pairs.append(("MACD falling", 20))
  elif is_long and raw["macd_hist"] > 0:
    pairs.append(("MACD positive", 10))
  elif not is_long and raw["macd_hist"] < 0:
    pairs.append(("MACD negative", 10))

  vr = raw["volume_ratio"]
  if vr >= 1.3:
    pairs.append(("volume surge", 15))
  elif vr >= 1.0:
    pairs.append(("volume at/above avg", 8))

  return pairs


def _signals_from_pairs(pairs: List[tuple[str, int]], raw: dict, zdist: float) -> List[str]:
  out: List[str] = []
  for token, _ in pairs:
    if token == "near zone":
      out.append(f"near zone ({zdist:.1f}% away)")
    elif token == "approaching zone":
      out.append(f"approaching zone ({zdist:.1f}%)")
    elif token == "RSI bullish reset":
      out.append(f"RSI {raw['rsi14']} bullish reset zone")
    elif token == "RSI momentum intact":
      out.append(f"RSI {raw['rsi14']} momentum intact")
    elif token == "RSI oversold bounce":
      out.append(f"RSI {raw['rsi14']} oversold bounce potential")
    elif token == "RSI bearish reset":
      out.append(f"RSI {raw['rsi14']} bearish reset zone")
    elif token == "RSI weakness intact":
      out.append(f"RSI {raw['rsi14']} weakness intact")
    elif token == "RSI overbought fade":
      out.append(f"RSI {raw['rsi14']} overbought fade potential")
    elif token == "above EMA20/50":
      out.append("price above EMA20/50")
    elif token == "above EMA20":
      out.append("price above EMA20")
    elif token == "EMA20 support":
      out.append("testing EMA20 support")
    elif token == "below EMA20/50":
      out.append("price below EMA20/50")
    elif token == "below EMA20":
      out.append("price below EMA20")
    elif token == "EMA20 resistance":
      out.append("testing EMA20 resistance")
    elif token == "MACD rising":
      out.append("MACD histogram rising")
    elif token == "MACD falling":
      out.append("MACD histogram falling")
    elif token == "MACD positive":
      out.append("MACD positive")
    elif token == "MACD negative":
      out.append("MACD negative")
    elif token == "volume surge":
      out.append(f"volume surge {raw['volume_ratio']:.1f}x avg")
    elif token == "volume at/above avg":
      out.append(f"volume at/above avg ({raw['volume_ratio']:.1f}x)")
    else:
      out.append(token)
  return out


def score_indicator_confluence(
  df: pd.DataFrame,
  direction: str,
  zone_low: float,
  zone_high: float,
  style: str,
) -> dict:
  """
  Score 0–100 for indicator alignment with trade direction.
  Used to unlock honest probe-tier executable when EW impulse pending.
  """
  if df is None or len(df) < 20:
    return {"score": 0, "aligned": False, "signals": [], "raw": {}, "zone_dist_pct": 99.0}

  raw = compute_raw_indicators(df)
  is_long = direction in ("LONG", "BULL")
  zdist = zone_proximity_pct(raw["price"], zone_low, zone_high)
  pairs = collect_indicator_signals(raw, direction, zdist)
  score = sum(pts for _, pts in pairs)
  signals = _signals_from_pairs(pairs, raw, zdist)

  thresholds = {"scalp": 62, "day_trade": 58, "swing": 55, "long_term": 52}
  threshold = thresholds.get(style, 58)

  return {
    "score": min(score, 100),
    "threshold": threshold,
    "aligned": score >= threshold,
    "signals": signals,
    "raw": raw,
    "zone_dist_pct": round(zdist, 3),
  }
