"""
TradingView-style order-flow & microstructure indicators (OSS logic).

Liquidity, CVD, footprint, TPO, volume profile, anchored VWAP — the modern
TV OSS edge layer. Uses OHLCV proxies when tick/L2 unavailable; upgrades
with live orderbook when exchange/WS data is present.
"""

from __future__ import annotations

from typing import Any, Dict, List, Optional, Tuple

import numpy as np
import pandas as pd


# Primary microstructure catalog — modern TV OSS focus
TV_MICROSTRUCTURE_CATALOG: Tuple[Dict[str, str], ...] = (
  {"id": "cvd", "role": "orderflow", "desc": "Cumulative Volume Delta — buy vs sell pressure"},
  {"id": "footprint", "role": "orderflow", "desc": "Footprint delta proxy — candle-level aggression"},
  {"id": "volume_profile", "role": "liquidity", "desc": "VP POC/VAH/VAL — high-volume nodes"},
  {"id": "tpo", "role": "liquidity", "desc": "TPO / Market Profile — time-at-price value area"},
  {"id": "anchored_vwap", "role": "anchor", "desc": "Anchored VWAP (TVWAP) — institutional pivot"},
  {"id": "liquidity_pools", "role": "liquidity", "desc": "Liquidity pools / stop clusters"},
  {"id": "hidden_liquidity", "role": "liquidity", "desc": "Hidden order / book wall proxy"},
  {"id": "delta_divergence", "role": "orderflow", "desc": "CVD divergence vs price"},
)


def _candle_delta(df: pd.DataFrame) -> pd.Series:
  """Proxy buy/sell volume split per bar (TV footprint approximation)."""
  o = df["Open"].astype(float)
  h = df["High"].astype(float)
  l = df["Low"].astype(float)
  c = df["Close"].astype(float)
  vol = df["Volume"].astype(float) if "Volume" in df.columns else pd.Series(1.0, index=df.index)
  hl = (h - l).replace(0, np.nan)
  buy_pct = (c - l) / hl
  buy_pct = buy_pct.clip(0, 1).fillna(0.5)
  buy_vol = vol * buy_pct
  sell_vol = vol * (1 - buy_pct)
  return buy_vol - sell_vol


def cumulative_volume_delta(df: pd.DataFrame, lookback: int = 50) -> Dict[str, Any]:
  """CVD — cumulative buy-minus-sell volume (OHLCV proxy)."""
  if df is None or len(df) < 10 or "Volume" not in df.columns:
    return {"available": False, "cvd": 0, "signal": "neutral"}

  delta = _candle_delta(df)
  cvd = delta.cumsum()
  recent = cvd.iloc[-lookback:] if len(cvd) >= lookback else cvd
  slope = float(recent.iloc[-1] - recent.iloc[0]) if len(recent) > 1 else 0.0
  val = float(cvd.iloc[-1])
  bar_delta = float(delta.iloc[-1])

  if slope > 0 and bar_delta > 0:
    signal = "bullish_absorption"
  elif slope < 0 and bar_delta < 0:
    signal = "bearish_distribution"
  elif slope > 0:
    signal = "bullish"
  elif slope < 0:
    signal = "bearish"
  else:
    signal = "neutral"

  return {
    "available": True,
    "cvd": round(val, 2),
    "cvd_slope": round(slope, 2),
    "bar_delta": round(bar_delta, 2),
    "signal": signal,
  }


def footprint_delta(df: pd.DataFrame, lookback: int = 10) -> Dict[str, Any]:
  """Footprint-style stacked delta over recent bars."""
  if df is None or len(df) < lookback + 2:
    return {"available": False, "signal": "neutral"}

  delta = _candle_delta(df)
  recent = delta.iloc[-lookback:]
  pos = float(recent[recent > 0].sum())
  neg = float(abs(recent[recent < 0].sum()))
  ratio = pos / neg if neg > 0 else (10.0 if pos > 0 else 1.0)
  stacked = float(recent.sum())

  if ratio > 1.5 and stacked > 0:
    signal = "buy_aggression"
  elif ratio < 0.67 and stacked < 0:
    signal = "sell_aggression"
  else:
    signal = "balanced"

  return {
    "available": True,
    "stacked_delta": round(stacked, 2),
    "buy_sell_ratio": round(ratio, 2),
    "signal": signal,
  }


def volume_profile(
  df: pd.DataFrame,
  bins: int = 24,
  value_area_pct: float = 0.70,
) -> Dict[str, Any]:
  """Volume Profile — POC, VAH, VAL from OHLCV distribution."""
  if df is None or len(df) < 20 or "Volume" not in df.columns:
    return {"available": False, "signal": "neutral"}

  typical = ((df["High"] + df["Low"] + df["Close"]) / 3).astype(float)
  vol = df["Volume"].astype(float)
  lo, hi = float(typical.min()), float(typical.max())
  if hi <= lo:
    return {"available": False, "signal": "neutral"}

  edges = np.linspace(lo, hi, bins + 1)
  hist = np.zeros(bins)
  for price, v in zip(typical.values, vol.values):
    if not np.isfinite(price) or not np.isfinite(v):
      continue
    idx = min(bins - 1, int((price - lo) / (hi - lo) * bins))
    hist[idx] += v

  poc_idx = int(np.argmax(hist))
  poc = float((edges[poc_idx] + edges[poc_idx + 1]) / 2)
  total = hist.sum()
  if total <= 0:
    return {"available": False, "signal": "neutral"}

  target = total * value_area_pct
  acc = hist[poc_idx]
  lo_i, hi_i = poc_idx, poc_idx
  while acc < target and (lo_i > 0 or hi_i < bins - 1):
    below = hist[lo_i - 1] if lo_i > 0 else -1
    above = hist[hi_i + 1] if hi_i < bins - 1 else -1
    if above >= below and hi_i < bins - 1:
      hi_i += 1
      acc += hist[hi_i]
    elif lo_i > 0:
      lo_i -= 1
      acc += hist[lo_i]
    else:
      break

  val = float(edges[lo_i])
  vah = float(edges[hi_i + 1])
  price = float(df["Close"].iloc[-1])

  if price < val:
    signal = "below_value_area"
  elif price > vah:
    signal = "above_value_area"
  elif abs(price - poc) / poc < 0.005:
    signal = "at_poc"
  else:
    signal = "inside_value_area"

  return {
    "available": True,
    "poc": round(poc, 8),
    "vah": round(vah, 8),
    "val": round(val, 8),
    "price_vs_poc_pct": round((price - poc) / poc * 100, 3),
    "signal": signal,
  }


def tpo_profile(df: pd.DataFrame, bins: int = 20) -> Dict[str, Any]:
  """TPO / Market Profile — time spent at price (bar-count proxy)."""
  if df is None or len(df) < 20:
    return {"available": False, "signal": "neutral"}

  typical = ((df["High"] + df["Low"] + df["Close"]) / 3).astype(float)
  lo, hi = float(typical.min()), float(typical.max())
  if hi <= lo:
    return {"available": False, "signal": "neutral"}

  edges = np.linspace(lo, hi, bins + 1)
  tpo = np.zeros(bins)
  for price in typical.values:
    if not np.isfinite(price):
      continue
    idx = min(bins - 1, int((price - lo) / (hi - lo) * bins))
    tpo[idx] += 1

  poc_idx = int(np.argmax(tpo))
  poc = float((edges[poc_idx] + edges[poc_idx + 1]) / 2)
  price = float(df["Close"].iloc[-1])

  # Single prints / poor highs — price at edge of TPO distribution
  if poc_idx <= 1:
    signal = "value_low"
  elif poc_idx >= bins - 2:
    signal = "value_high"
  elif price > poc:
    signal = "above_poc"
  elif price < poc:
    signal = "below_poc"
  else:
    signal = "at_poc"

  return {
    "available": True,
    "tpo_poc": round(poc, 8),
    "tpo_bins": bins,
    "signal": signal,
  }


def anchored_vwap(df: pd.DataFrame, anchor_bars: int = 50) -> Dict[str, Any]:
  """Anchored VWAP (TVWAP) from swing anchor — popular TV OSS."""
  if df is None or len(df) < anchor_bars + 5 or "Volume" not in df.columns:
    return {"available": False, "signal": "neutral"}

  segment = df.iloc[-anchor_bars:]
  tp = (segment["High"] + segment["Low"] + segment["Close"]) / 3
  vol = segment["Volume"].astype(float).replace(0, np.nan)
  avwap = (tp.astype(float) * vol).sum() / vol.sum()
  price = float(df["Close"].iloc[-1])
  if not np.isfinite(avwap) or avwap <= 0:
    return {"available": False, "signal": "neutral"}

  dist = (price - avwap) / avwap * 100
  if dist > 1.0:
    signal = "above_avwap"
  elif dist < -1.0:
    signal = "below_avwap"
  else:
    signal = "at_avwap"

  return {
    "available": True,
    "avwap": round(float(avwap), 8),
    "dist_pct": round(dist, 3),
    "anchor_bars": anchor_bars,
    "signal": signal,
  }


def liquidity_pools(df: pd.DataFrame, lookback: int = 40) -> Dict[str, Any]:
  """Liquidity pools — swing highs/lows where stops cluster."""
  if df is None or len(df) < lookback + 5:
    return {"available": False, "signal": "neutral"}

  high = df["High"].astype(float)
  low = df["Low"].astype(float)
  close = df["Close"].astype(float)
  vol = df["Volume"].astype(float) if "Volume" in df.columns else pd.Series(1.0, index=df.index)

  seg_h = high.iloc[-lookback:]
  seg_l = low.iloc[-lookback:]
  seg_v = vol.iloc[-lookback:]

  pool_high = float(seg_h.nlargest(3).mean())
  pool_low = float(seg_l.nsmallest(3).mean())
  price = float(close.iloc[-1])
  vol_at_extreme = float(seg_v[seg_h >= seg_h.quantile(0.9)].sum())

  dist_high = (pool_high - price) / price * 100
  dist_low = (price - pool_low) / price * 100

  if dist_low < 1.5 and vol_at_extreme > seg_v.median() * 2:
    signal = "liquidity_below"  # sell-side liquidity sweep zone
  elif dist_high < 1.5:
    signal = "liquidity_above"
  else:
    signal = "between_pools"

  return {
    "available": True,
    "pool_high": round(pool_high, 8),
    "pool_low": round(pool_low, 8),
    "dist_high_pct": round(dist_high, 3),
    "dist_low_pct": round(dist_low, 3),
    "signal": signal,
  }


def hidden_liquidity_proxy(
  orderbook: Optional[dict] = None,
  *,
  imbalance_threshold: float = 0.20,
) -> Dict[str, Any]:
  """Hidden order / book wall proxy from L2 imbalance."""
  if not orderbook or not orderbook.get("available"):
    return {"available": False, "signal": "no_book_data"}

  imb = float(orderbook.get("imbalance") or 0)
  bid_vol = orderbook.get("bid_vol", 0)
  ask_vol = orderbook.get("ask_vol", 0)

  if imb > imbalance_threshold:
    signal = "hidden_bid_wall"
  elif imb < -imbalance_threshold:
    signal = "hidden_ask_wall"
  else:
    signal = "balanced_book"

  return {
    "available": True,
    "imbalance": round(imb, 3),
    "bid_vol": bid_vol,
    "ask_vol": ask_vol,
    "signal": signal,
  }


def cvd_divergence(df: pd.DataFrame, lookback: int = 20) -> Dict[str, Any]:
  """CVD divergence vs price — key TV order-flow signal."""
  if df is None or len(df) < lookback + 5:
    return {"available": False, "signal": "none"}

  close = df["Close"].astype(float)
  delta = _candle_delta(df)
  cvd = delta.cumsum()

  p0, p1 = float(close.iloc[-lookback]), float(close.iloc[-1])
  c0, c1 = float(cvd.iloc[-lookback]), float(cvd.iloc[-1])

  if p1 < p0 and c1 > c0:
    signal = "bullish_cvd_div"
  elif p1 > p0 and c1 < c0:
    signal = "bearish_cvd_div"
  else:
    signal = "none"

  return {"available": True, "signal": signal, "price_chg_pct": round((p1 - p0) / p0 * 100, 3)}


def compute_microstructure_signals(
  df: pd.DataFrame,
  orderbook: Optional[dict] = None,
) -> Dict[str, Any]:
  """Bundle all order-flow / liquidity TV OSS signals."""
  return {
    "cvd": cumulative_volume_delta(df),
    "footprint": footprint_delta(df),
    "volume_profile": volume_profile(df),
    "tpo": tpo_profile(df),
    "anchored_vwap": anchored_vwap(df),
    "liquidity_pools": liquidity_pools(df),
    "hidden_liquidity": hidden_liquidity_proxy(orderbook),
    "cvd_divergence": cvd_divergence(df),
    "catalog": [c["id"] for c in TV_MICROSTRUCTURE_CATALOG],
  }


def score_microstructure_confluence(
  ms: Dict[str, Any],
  direction: str,
) -> Dict[str, Any]:
  """Score 0–100 microstructure alignment with trade direction."""
  is_long = direction.upper() in ("LONG", "BULL")
  score = 25
  notes: List[str] = []

  cvd = ms.get("cvd") or {}
  if cvd.get("available"):
    sig = cvd.get("signal", "")
    if (is_long and "bullish" in sig) or (not is_long and "bearish" in sig):
      score += 15
      notes.append(f"CVD {sig}")
    elif (is_long and "bearish" in sig) or (not is_long and "bullish" in sig):
      score -= 12
      notes.append(f"CVD opposes ({sig})")

  fp = ms.get("footprint") or {}
  if fp.get("available"):
    if (is_long and fp["signal"] == "buy_aggression") or (not is_long and fp["signal"] == "sell_aggression"):
      score += 12
      notes.append(f"footprint {fp['signal']}")
    elif fp["signal"] != "balanced":
      score -= 8
      notes.append(f"footprint opposes")

  vp = ms.get("volume_profile") or {}
  if vp.get("available"):
    if is_long and vp["signal"] in ("below_value_area", "at_poc"):
      score += 10
      notes.append(f"VP {vp['signal']} POC={vp.get('poc')}")
    elif not is_long and vp["signal"] in ("above_value_area", "at_poc"):
      score += 10
      notes.append(f"VP {vp['signal']}")
    elif vp["signal"] == "inside_value_area":
      score += 3

  tpo = ms.get("tpo") or {}
  if tpo.get("available"):
    if (is_long and tpo["signal"] in ("below_poc", "value_low")) or (
      not is_long and tpo["signal"] in ("above_poc", "value_high")
    ):
      score += 8
      notes.append(f"TPO {tpo['signal']}")

  av = ms.get("anchored_vwap") or {}
  if av.get("available"):
    if is_long and av["signal"] in ("below_avwap", "at_avwap"):
      score += 8
      notes.append(f"AVWAP {av['dist_pct']:+.1f}%")
    elif not is_long and av["signal"] in ("above_avwap", "at_avwap"):
      score += 8
      notes.append(f"AVWAP {av['dist_pct']:+.1f}%")

  liq = ms.get("liquidity_pools") or {}
  if liq.get("available"):
    if is_long and liq["signal"] == "liquidity_below":
      score += 6
      notes.append("liquidity sweep below (long setup)")
    elif not is_long and liq["signal"] == "liquidity_above":
      score += 6
      notes.append("liquidity sweep above (short setup)")

  hid = ms.get("hidden_liquidity") or {}
  if hid.get("available"):
    if (is_long and hid["signal"] == "hidden_bid_wall") or (
      not is_long and hid["signal"] == "hidden_ask_wall"
    ):
      score += 10
      notes.append(f"hidden liquidity {hid['signal']}")
    elif hid["signal"] != "balanced_book":
      score -= 5

  div = ms.get("cvd_divergence") or {}
  if div.get("signal") == "bullish_cvd_div" and is_long:
    score += 12
    notes.append("bullish CVD divergence")
  elif div.get("signal") == "bearish_cvd_div" and not is_long:
    score += 12
    notes.append("bearish CVD divergence")
  elif div.get("signal") != "none":
    score -= 8
    notes.append(f"CVD div opposes ({motion})" if (motion := div.get("signal")) else "")

  score = max(0, min(100, score))
  return {
    "score": score,
    "aligned": score >= 55,
    "signals": notes,
    "raw": ms,
  }
