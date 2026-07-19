"""
TradingView-style open-source indicator ports (pure pandas).

Complementary OSS stack (integrate + collaborate, not sprawl):
  Trend:     Supertrend, Hull MA, Chandelier Exit
  Volatility: Bollinger %B, TTM Squeeze (BB inside Keltner)
  Strength:  ADX
  Momentum:  RSI
  Anchor:    VWAP distance
"""

from __future__ import annotations

import os
from typing import Any, Dict, List, Optional, Tuple

import numpy as np
import pandas as pd


# Registry — each indicator complements EW; none replaces it
TV_OSS_CATALOG: Tuple[Dict[str, str], ...] = (
  {"id": "supertrend", "role": "trend", "desc": "ATR trailing trend flip"},
  {"id": "chandelier", "role": "trend", "desc": "Chandelier Exit ATR stop — confirms Supertrend"},
  {"id": "hull_ma", "role": "trend", "desc": "Hull MA — fast adaptive trend filter"},
  {"id": "bollinger", "role": "volatility", "desc": "Bollinger %B band position"},
  {"id": "ttm_squeeze", "role": "volatility", "desc": "TTM Squeeze — BB inside Keltner compression"},
  {"id": "adx", "role": "strength", "desc": "ADX trend strength + DI bias"},
  {"id": "rsi", "role": "momentum", "desc": "RSI — momentum not fighting direction"},
  {"id": "vwap", "role": "anchor", "desc": "VWAP institutional anchor"},
)

# Exploration pool — dynamic value candidates not yet promoted to active stack
TV_OSS_CANDIDATES: Tuple[Dict[str, Any], ...] = (
  {"id": "cmf", "role": "flow", "desc": "Chaikin Money Flow — volume conviction", "pine_ref": "Chaikin Money Flow"},
  {"id": "williams_r", "role": "momentum", "desc": "Williams %R — fast overbought/oversold", "pine_ref": "Williams %R"},
  {"id": "aroon", "role": "strength", "desc": "Aroon — trend emergence timing", "pine_ref": "Aroon"},
  {"id": "stoch_rsi", "role": "momentum", "desc": "Stochastic RSI — sensitive momentum", "pine_ref": "Stoch RSI"},
  {"id": "obv_trend", "role": "flow", "desc": "OBV slope — volume flow confirmation", "pine_ref": "On Balance Volume"},
  {"id": "wavetrend", "role": "momentum", "desc": "WaveTrend — CT momentum oscillator", "pine_ref": "WaveTrend"},
  {"id": "keltner_break", "role": "volatility", "desc": "Keltner channel breakout", "pine_ref": "Keltner Channels"},
  {"id": "fisher", "role": "momentum", "desc": "Fisher Transform — Gaussian normalized momentum", "pine_ref": "Fisher Transform"},
)


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


def _wma(series: pd.Series, period: int) -> pd.Series:
  if period < 1 or len(series) < period:
    return pd.Series(dtype=float)
  weights = np.arange(1, period + 1, dtype=float)
  return series.rolling(period).apply(lambda x: np.dot(x, weights) / weights.sum(), raw=True)


def hull_ma_trend(df: pd.DataFrame, period: int = 21) -> Dict[str, Any]:
  """Hull MA — responsive trend (popular TV OSS)."""
  if df is None or len(df) < period + 5:
    return {"available": False, "signal": "neutral", "slope": 0}

  close = df["Close"].astype(float)
  half = max(2, period // 2)
  sqrt_p = max(2, int(np.sqrt(period)))
  raw = 2 * _wma(close, half) - _wma(close, period)
  hma = _wma(raw, sqrt_p)
  if len(hma.dropna()) < 3:
    return {"available": False, "signal": "neutral", "slope": 0}

  val = float(hma.iloc[-1])
  prev = float(hma.iloc[-3])
  price = float(close.iloc[-1])
  slope = (val - prev) / prev * 100 if prev else 0
  if price > val and slope > 0:
    signal = "bullish"
  elif price < val and slope < 0:
    signal = "bearish"
  elif price > val:
    signal = "bullish"
  elif price < val:
    signal = "bearish"
  else:
    signal = "neutral"
  return {"available": True, "value": round(val, 8), "signal": signal, "slope": round(slope, 4)}


def chandelier_exit(df: pd.DataFrame, period: int = 22, mult: float = 3.0) -> Dict[str, Any]:
  """Chandelier Exit — ATR trail complement to Supertrend."""
  if df is None or len(df) < period + 2:
    return {"available": False, "signal": "neutral"}

  high = df["High"].astype(float)
  low = df["Low"].astype(float)
  close = df["Close"].astype(float)
  atr = atr_series(df, 14)
  long_stop = high.rolling(period).max() - mult * atr
  short_stop = low.rolling(period).min() + mult * atr
  c = float(close.iloc[-1])
  ls = float(long_stop.iloc[-1])
  ss = float(short_stop.iloc[-1])
  if c > ls:
    signal = "bullish"
  elif c < ss:
    signal = "bearish"
  else:
    signal = "neutral"
  return {
    "available": True,
    "long_stop": round(ls, 8),
    "short_stop": round(ss, 8),
    "signal": signal,
  }


def rsi_oscillator(df: pd.DataFrame, period: int = 14) -> Dict[str, Any]:
  if df is None or len(df) < period + 2:
    return {"available": False, "value": 50, "signal": "neutral"}

  close = df["Close"].astype(float)
  delta = close.diff()
  gain = delta.clip(lower=0).rolling(period).mean()
  loss = (-delta.clip(upper=0)).rolling(period).mean()
  rs = gain / loss.replace(0, np.nan)
  rsi = 100 - (100 / (1 + rs))
  val = float(rsi.iloc[-1]) if np.isfinite(rsi.iloc[-1]) else 50.0
  if val <= 30:
    signal = "oversold"
  elif val >= 70:
    signal = "overbought"
  elif val < 45:
    signal = "weak"
  elif val > 55:
    signal = "strong"
  else:
    signal = "neutral"
  return {"available": True, "value": round(val, 2), "signal": signal}


def vwap_anchor(df: pd.DataFrame) -> Dict[str, Any]:
  """Session VWAP anchor — institutional mean."""
  if df is None or len(df) < 5 or "Volume" not in df.columns:
    return {"available": False, "dist_pct": 0, "signal": "neutral"}

  typical = (df["High"] + df["Low"] + df["Close"]) / 3
  vol = df["Volume"].astype(float).replace(0, np.nan)
  cum_vol = vol.cumsum()
  cum_tp = (typical.astype(float) * vol).cumsum()
  vwap = cum_tp / cum_vol
  price = float(df["Close"].iloc[-1])
  v = float(vwap.iloc[-1])
  if not np.isfinite(v) or v <= 0:
    return {"available": False, "dist_pct": 0, "signal": "neutral"}
  dist = (price - v) / v * 100
  if dist > 1.5:
    signal = "above_vwap"
  elif dist < -1.5:
    signal = "below_vwap"
  else:
    signal = "at_vwap"
  return {"available": True, "vwap": round(v, 8), "dist_pct": round(dist, 3), "signal": signal}


def ttm_squeeze(
  df: pd.DataFrame,
  bb_period: int = 20,
  kc_period: int = 20,
  kc_mult: float = 1.5,
) -> Dict[str, Any]:
  """
  TTM Squeeze — Bollinger inside Keltner = compression.
  Momentum histogram via linear regression of (close - mid).
  """
  if df is None or len(df) < kc_period + 5:
    return {"available": False, "squeeze_on": False, "momentum": 0, "signal": "neutral"}

  close = df["Close"].astype(float)
  mid = close.rolling(bb_period).mean()
  std = close.rolling(bb_period).std()
  bb_upper = mid + 2 * std
  bb_lower = mid - 2 * std
  atr = atr_series(df, kc_period)
  kc_upper = mid + kc_mult * atr
  kc_lower = mid - kc_mult * atr
  squeeze_on = bool(bb_upper.iloc[-1] < kc_upper.iloc[-1] and bb_lower.iloc[-1] > kc_lower.iloc[-1])

  # Momentum: linreg slope of (close - mid) over last 12 bars
  diff = (close - mid).iloc[-12:]
  if len(diff.dropna()) < 5:
    mom = 0.0
  else:
    x = np.arange(len(diff))
    y = diff.values.astype(float)
    mask = np.isfinite(y)
    if mask.sum() < 3:
      mom = 0.0
    else:
      coef = np.polyfit(x[mask], y[mask], 1)
      mom = float(coef[0])

  if squeeze_on:
    signal = "squeeze_on"
  elif mom > 0:
    signal = "momentum_up"
  elif mom < 0:
    signal = "momentum_down"
  else:
    signal = "neutral"
  return {
    "available": True,
    "squeeze_on": squeeze_on,
    "momentum": round(mom, 8),
    "signal": signal,
    "release": not squeeze_on and abs(mom) > 0,
  }


def chaikin_mf(df: pd.DataFrame, period: int = 20) -> Dict[str, Any]:
  """Chaikin Money Flow — volume-weighted accumulation/distribution."""
  if df is None or len(df) < period + 2 or "Volume" not in df.columns:
    return {"available": False, "value": 0, "signal": "neutral"}

  high = df["High"].astype(float)
  low = df["Low"].astype(float)
  close = df["Close"].astype(float)
  vol = df["Volume"].astype(float)
  hl = (high - low).replace(0, np.nan)
  mfm = ((close - low) - (high - close)) / hl
  mfv = mfm * vol
  cmf = mfv.rolling(period).sum() / vol.rolling(period).sum()
  val = float(cmf.iloc[-1]) if np.isfinite(cmf.iloc[-1]) else 0.0
  if val > 0.1:
    signal = "accumulation"
  elif val < -0.1:
    signal = "distribution"
  else:
    signal = "neutral"
  return {"available": True, "value": round(val, 4), "signal": signal}


def williams_r(df: pd.DataFrame, period: int = 14) -> Dict[str, Any]:
  if df is None or len(df) < period + 1:
    return {"available": False, "value": -50, "signal": "neutral"}

  high = df["High"].astype(float).rolling(period).max()
  low = df["Low"].astype(float).rolling(period).min()
  close = df["Close"].astype(float)
  wr = -100 * (high - close) / (high - low).replace(0, np.nan)
  val = float(wr.iloc[-1]) if np.isfinite(wr.iloc[-1]) else -50.0
  if val <= -80:
    signal = "oversold"
  elif val >= -20:
    signal = "overbought"
  else:
    signal = "neutral"
  return {"available": True, "value": round(val, 2), "signal": signal}


def aroon(df: pd.DataFrame, period: int = 25) -> Dict[str, Any]:
  if df is None or len(df) < period + 5:
    return {"available": False, "signal": "neutral", "spread": 0}

  high = df["High"].astype(float)
  low = df["Low"].astype(float)
  aroon_up = 100 * high.rolling(period + 1).apply(lambda x: x.argmax() / period, raw=True)
  aroon_down = 100 * low.rolling(period + 1).apply(lambda x: x.argmin() / period, raw=True)
  up = float(aroon_up.iloc[-1])
  down = float(aroon_down.iloc[-1])
  spread = up - down
  if up > 70 and spread > 25:
    signal = "bullish"
  elif down > 70 and spread < -25:
    signal = "bearish"
  else:
    signal = "neutral"
  return {"available": True, "aroon_up": round(up, 1), "aroon_down": round(down, 1), "spread": round(spread, 1), "signal": signal}


def stoch_rsi(df: pd.DataFrame, period: int = 14) -> Dict[str, Any]:
  if df is None or len(df) < period * 2 + 5:
    return {"available": False, "value": 0.5, "signal": "neutral"}

  close = df["Close"].astype(float)
  delta = close.diff()
  gain = delta.clip(lower=0).rolling(period).mean()
  loss = (-delta.clip(upper=0)).rolling(period).mean()
  rs = gain / loss.replace(0, np.nan)
  rsi = 100 - (100 / (1 + rs))
  rsi_min = rsi.rolling(period).min()
  rsi_max = rsi.rolling(period).max()
  stoch = (rsi - rsi_min) / (rsi_max - rsi_min).replace(0, np.nan)
  val = float(stoch.iloc[-1]) if np.isfinite(stoch.iloc[-1]) else 0.5
  if val <= 0.2:
    signal = "oversold"
  elif val >= 0.8:
    signal = "overbought"
  else:
    signal = "neutral"
  return {"available": True, "value": round(val, 4), "signal": signal}


def obv_trend(df: pd.DataFrame, lookback: int = 14) -> Dict[str, Any]:
  if df is None or len(df) < lookback + 5 or "Volume" not in df.columns:
    return {"available": False, "slope": 0, "signal": "neutral"}

  close = df["Close"].astype(float)
  vol = df["Volume"].astype(float)
  direction = np.sign(close.diff()).fillna(0)
  obv = (direction * vol).cumsum()
  recent = obv.iloc[-lookback:]
  x = np.arange(len(recent))
  coef = np.polyfit(x, recent.values.astype(float), 1)
  slope = float(coef[0])
  if slope > 0:
    signal = "bullish"
  elif slope < 0:
    signal = "bearish"
  else:
    signal = "neutral"
  return {"available": True, "slope": round(slope, 2), "signal": signal}


def wavetrend(df: pd.DataFrame, channel: int = 10, avg: int = 21) -> Dict[str, Any]:
  """WaveTrend oscillator — popular TV OSS momentum."""
  if df is None or len(df) < channel + avg + 5:
    return {"available": False, "wt1": 0, "wt2": 0, "signal": "neutral"}

  hlc3 = (df["High"] + df["Low"] + df["Close"]) / 3
  hlc3 = hlc3.astype(float)
  esa = hlc3.ewm(span=channel, adjust=False).mean()
  d = (hlc3 - esa).abs().ewm(span=channel, adjust=False).mean()
  ci = (hlc3 - esa) / (0.015 * d.replace(0, np.nan))
  wt1 = ci.ewm(span=avg, adjust=False).mean()
  wt2 = wt1.rolling(4).mean()
  w1 = float(wt1.iloc[-1])
  w2 = float(wt2.iloc[-1]) if np.isfinite(wt2.iloc[-1]) else w1
  if w1 > w2 and w1 < -50:
    signal = "bullish"
  elif w1 < w2 and w1 > 50:
    signal = "bearish"
  else:
    signal = "neutral"
  return {"available": True, "wt1": round(w1, 2), "wt2": round(w2, 2), "signal": signal}


_EXPLORATION_FN = {
  "cmf": chaikin_mf,
  "williams_r": williams_r,
  "aroon": aroon,
  "stoch_rsi": stoch_rsi,
  "obv_trend": obv_trend,
  "wavetrend": wavetrend,
}


def compute_exploration_signals(df: pd.DataFrame) -> Dict[str, Any]:
  """Compute exploration-pool TV OSS indicators for dynamic value scoring."""
  out: Dict[str, Any] = {}
  for cand in TV_OSS_CANDIDATES:
    fn = _EXPLORATION_FN.get(cand["id"])
    if fn:
      out[cand["id"]] = fn(df)
    else:
      out[cand["id"]] = {"available": False, "signal": "not_implemented"}
  return out


def score_candidate_alignment(indicator_id: str, sig: dict, direction: str) -> int:
  """Score 0-100 how well an exploration indicator aligns with direction."""
  if not sig.get("available"):
    return 0
  is_long = direction.upper() in ("LONG", "BULL")
  signal = sig.get("signal", "neutral")

  bullish = signal in (
    "bullish", "accumulation", "oversold", "momentum_up",
    "bullish_absorption", "buy_aggression", "below_value_area", "below_poc",
    "value_low", "below_avwap", "at_avwap", "liquidity_below",
    "hidden_bid_wall", "bullish_cvd_div",
  )
  bearish = signal in (
    "bearish", "distribution", "overbought", "momentum_down",
    "bearish_distribution", "sell_aggression", "above_value_area", "above_poc",
    "value_high", "above_avwap", "liquidity_above",
    "hidden_ask_wall", "bearish_cvd_div",
  )

  if (is_long and bullish) or (not is_long and bearish):
    return 75
  if signal == "neutral":
    return 40
  if (is_long and bearish) or (not is_long and bullish):
    return 15
  return 50


def compute_tv_signals(df: pd.DataFrame, orderbook: Optional[dict] = None) -> Dict[str, Any]:
  """Bundle TV-style signals for one OHLCV frame."""
  st = supertrend(df)
  bb = bollinger_bands(df)
  ax = adx(df)
  ch = chandelier_exit(df)
  hm = hull_ma_trend(df)
  rs = rsi_oscillator(df)
  vw = vwap_anchor(df)
  sq = ttm_squeeze(df)
  atr = atr_series(df) if df is not None and len(df) >= 15 else pd.Series(dtype=float)
  atr_pct = 0.0
  if len(atr) and df is not None:
    price = float(df["Close"].iloc[-1])
    if price > 0:
      atr_pct = float(atr.iloc[-1] / price * 100)

  out = {
    "supertrend": st,
    "bollinger": bb,
    "adx": ax,
    "chandelier": ch,
    "hull_ma": hm,
    "rsi": rs,
    "vwap": vw,
    "ttm_squeeze": sq,
    "atr_pct": round(atr_pct, 3),
    "catalog": [c["id"] for c in TV_OSS_CATALOG],
  }
  if os.environ.get("EW_TV_MICROSTRUCTURE", "1").lower() not in ("0", "false", "no"):
    try:
      from core.tv_microstructure import compute_microstructure_signals

      out["microstructure"] = compute_microstructure_signals(df, orderbook)
    except Exception as exc:
      out["microstructure"] = {"available": False, "error": str(exc)}
  return out


def score_tv_confluence(
  df: pd.DataFrame,
  direction: str,
  *,
  layer_weights: Optional[Dict[str, float]] = None,
  orderbook: Optional[dict] = None,
) -> Dict[str, Any]:
  """
  Score 0–100: complementary TV OSS layers aligned with trade direction.
  Trend + volatility + strength + momentum + anchor collaborate with EW.
  """
  signals = compute_tv_signals(df, orderbook=orderbook)
  is_long = direction.upper() in ("LONG", "BULL")
  weights = layer_weights or _default_layer_weights()
  layer_scores: Dict[str, int] = {}
  notes: List[str] = []

  # --- Trend layer: Supertrend + Chandelier + Hull MA ---
  trend_pts = 0
  st = signals["supertrend"]
  if st.get("available"):
    if (is_long and st["direction"] > 0) or (not is_long and st["direction"] < 0):
      trend_pts += 12
      notes.append(f"supertrend {st['signal']}")
    elif st["direction"] != 0:
      trend_pts -= 8
      notes.append(f"supertrend opposes ({st['signal']})")
    if st.get("flip"):
      notes.append("supertrend flip (caution)")

  ch = signals.get("chandelier") or {}
  if ch.get("available"):
    if (is_long and ch["signal"] == "bullish") or (not is_long and ch["signal"] == "bearish"):
      trend_pts += 8
      notes.append(f"chandelier {ch['signal']}")
    elif ch["signal"] != "neutral":
      trend_pts -= 5
      notes.append(f"chandelier opposes ({ch['signal']})")

  hm = signals.get("hull_ma") or {}
  if hm.get("available"):
    if (is_long and hm["signal"] == "bullish") or (not is_long and hm["signal"] == "bearish"):
      trend_pts += 5
      notes.append(f"hull_ma {hm['signal']}")
  layer_scores["trend"] = max(-15, min(25, trend_pts))

  # --- Volatility layer: BB + TTM Squeeze ---
  vol_pts = 0
  bb = signals["bollinger"]
  if bb.get("available"):
    if is_long and bb["pct_b"] < 0.35:
      vol_pts += 10
      notes.append(f"BB %B {bb['pct_b']:.2f} favorable long")
    elif not is_long and bb["pct_b"] > 0.65:
      vol_pts += 10
      notes.append(f"BB %B {bb['pct_b']:.2f} favorable short")
    elif is_long and bb["signal"] == "overbought":
      vol_pts -= 8
      notes.append("BB overbought vs long")
    elif not is_long and bb["signal"] == "oversold":
      vol_pts -= 8
      notes.append("BB oversold vs short")

  sq = signals.get("ttm_squeeze") or {}
  if sq.get("available"):
    if sq.get("squeeze_on"):
      vol_pts -= 4
      notes.append("TTM squeeze on (wait for release)")
    elif sq.get("release"):
      if (is_long and sq.get("momentum", 0) > 0) or (not is_long and sq.get("momentum", 0) < 0):
        vol_pts += 8
        notes.append("TTM squeeze release aligned")
  layer_scores["volatility"] = max(-12, min(18, vol_pts))

  # --- Strength: ADX ---
  str_pts = 0
  ax = signals["adx"]
  if ax.get("available"):
    if ax["trend"] == "strong":
      if (is_long and ax["di_bias"] == "bull") or (not is_long and ax["di_bias"] == "bear"):
        str_pts += 15
        notes.append(f"ADX {ax['adx']:.0f} trend aligned")
      else:
        str_pts += 3
        notes.append("ADX strong but DI mixed")
    elif ax["trend"] == "weak":
      str_pts -= 8
      notes.append(f"ADX {ax['adx']:.0f} choppy — tighten risk")
  layer_scores["strength"] = max(-10, min(15, str_pts))

  # --- Momentum: RSI ---
  mom_pts = 0
  rs = signals.get("rsi") or {}
  if rs.get("available"):
    rv = rs["value"]
    if is_long and rv < 40:
      mom_pts += 6
      notes.append(f"RSI {rv:.0f} room to run long")
    elif not is_long and rv > 60:
      mom_pts += 6
      notes.append(f"RSI {rv:.0f} room to run short")
    elif is_long and rs["signal"] == "overbought":
      mom_pts -= 6
      notes.append("RSI overbought vs long")
    elif not is_long and rs["signal"] == "oversold":
      mom_pts -= 6
      notes.append("RSI oversold vs short")
  layer_scores["momentum"] = max(-8, min(8, mom_pts))

  # --- Anchor: VWAP ---
  anc_pts = 0
  vw = signals.get("vwap") or {}
  if vw.get("available"):
    if is_long and vw["signal"] in ("below_vwap", "at_vwap"):
      anc_pts += 5
      notes.append(f"VWAP {vw['dist_pct']:+.1f}% favorable long entry")
    elif not is_long and vw["signal"] in ("above_vwap", "at_vwap"):
      anc_pts += 5
      notes.append(f"VWAP {vw['dist_pct']:+.1f}% favorable short entry")
    elif is_long and vw["signal"] == "above_vwap":
      anc_pts += 2
      notes.append("above VWAP trend long")
    elif not is_long and vw["signal"] == "below_vwap":
      anc_pts += 2
      notes.append("below VWAP trend short")
  layer_scores["anchor"] = max(-5, min(7, anc_pts))

  # --- Dynamic exploration layer (promoted candidates) ---
  flow_pts = 0
  try:
    from engine.tv_oss_discovery import load_tv_oss_discovery

    promoted = load_tv_oss_discovery().get("all_promoted_exploration") or []
    if not promoted:
      from engine.tv_oss_consensus import load_tv_oss_consensus

      promoted = load_tv_oss_consensus().get("promoted_exploration") or []
    if promoted:
      exp = compute_exploration_signals(df)
      for pid in promoted[:3]:
        sig = exp.get(pid) or {}
        align = score_candidate_alignment(pid, sig, direction)
        if align >= 70:
          flow_pts += 5
          notes.append(f"explore:{pid} {sig.get('signal')} aligned")
        elif align <= 20:
          flow_pts -= 4
          notes.append(f"explore:{pid} opposes")
  except Exception:
    pass
  if flow_pts:
    layer_scores["flow"] = max(-8, min(10, flow_pts))

  # --- Microstructure layer (CVD, VP, TPO, liquidity, footprint) ---
  ms_raw = signals.get("microstructure")
  if ms_raw and ms_raw.get("cvd", {}).get("available"):
    try:
      from core.tv_microstructure import score_microstructure_confluence

      ms = score_microstructure_confluence(ms_raw, direction)
      ms_pts = int((ms.get("score", 50) - 50) * 0.35)
      layer_scores["microstructure"] = max(-12, min(18, ms_pts))
      notes.extend(ms.get("signals", [])[:4])
    except Exception:
      pass

  # Weighted composite + baseline
  raw = sum(layer_scores.get(k, 0) * weights.get(k, 1.0) for k in layer_scores)
  score = max(0, min(100, int(raw + 30)))

  atr_pct = signals.get("atr_pct", 0)
  if atr_pct > 5:
    notes.append(f"high vol ATR%={atr_pct}")
  elif atr_pct < 1:
    notes.append(f"low vol ATR%={atr_pct}")

  aligned = score >= 55
  return {
    "score": score,
    "aligned": aligned,
    "signals": notes,
    "layers": layer_scores,
    "raw": signals,
    "atr_pct": atr_pct,
    "catalog": TV_OSS_CATALOG,
  }


def _default_layer_weights() -> Dict[str, float]:
  """Balanced layer weights — overridable via TV OSS executive consensus."""
  raw = os.environ.get("EW_TV_LAYER_WEIGHTS", "")
  if raw.strip():
    try:
      import json
      return json.loads(raw)
    except (json.JSONDecodeError, TypeError):
      pass
  return {"trend": 1.0, "volatility": 1.0, "strength": 1.0, "momentum": 0.9, "anchor": 0.85, "flow": 0.85, "microstructure": 1.15}
