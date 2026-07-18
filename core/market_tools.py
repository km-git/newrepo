"""Supplementary market tools — layered on top of Elliott Wave (always-on)."""

from __future__ import annotations

from typing import Any, Dict, List, Optional

import numpy as np
import pandas as pd

from core.indicators import compute_raw_indicators, rsi14


def vwap_distance_pct(df: pd.DataFrame) -> float:
  if df is None or len(df) < 5 or "Volume" not in df.columns:
    return 0.0
  tp = (df["High"] + df["Low"] + df["Close"]) / 3
  vol = df["Volume"].astype(float).replace(0, np.nan)
  cum_vol = vol.cumsum()
  cum_tp_vol = (tp * vol).cumsum()
  vwap = cum_tp_vol / cum_vol
  price = float(df["Close"].iloc[-1])
  v = float(vwap.iloc[-1])
  if not np.isfinite(v) or v == 0:
    return 0.0
  return round((price - v) / v * 100, 3)


def detect_rsi_divergence(df: pd.DataFrame, lookback: int = 20) -> Optional[str]:
  """Simple RSI divergence vs price over lookback window."""
  if df is None or len(df) < lookback + 5:
    return None
  close = df["Close"].astype(float)
  segment = close.iloc[-lookback:]
  rsi_vals = []
  for i in range(len(segment)):
    sub = close.iloc[: len(close) - lookback + i + 1]
    if len(sub) < 15:
      continue
    rsi_vals.append(rsi14(sub))
  if len(rsi_vals) < 5:
    return None

  p0, p1 = float(segment.iloc[0]), float(segment.iloc[-1])
  r0, r1 = rsi_vals[0], rsi_vals[-1]
  if p1 < p0 and r1 > r0:
    return "bullish_divergence"
  if p1 > p0 and r1 < r0:
    return "bearish_divergence"
  return None


def multi_tf_rsi_stack(data: Dict[str, pd.DataFrame], tfs: List[str]) -> dict:
  """RSI alignment across timeframes."""
  stack = {}
  for tf in tfs:
    if tf not in data or len(data[tf]) < 20:
      stack[tf] = None
      continue
    stack[tf] = rsi14(data[tf]["Close"].astype(float))
  vals = [v for v in stack.values() if v is not None]
  bull = sum(1 for v in vals if v < 45)
  bear = sum(1 for v in vals if v > 55)
  neutral = len(vals) - bull - bear
  bias = "BULL" if bull > bear else "BEAR" if bear > bull else "NEUTRAL"
  return {"by_tf": stack, "bias": bias, "bull_count": bull, "bear_count": bear, "neutral_count": neutral}


def btc_correlation(symbol: str, df_1d: pd.DataFrame, btc_df: Optional[pd.DataFrame], window: int = 30) -> dict:
  if symbol.startswith("BTC") or btc_df is None or len(df_1d) < window or len(btc_df) < window:
    return {"available": False, "correlation": None, "aligned": None}
  a = df_1d["Close"].astype(float).pct_change().iloc[-window:]
  b = btc_df["Close"].astype(float).pct_change().iloc[-window:]
  n = min(len(a), len(b))
  if n < 10:
    return {"available": False, "correlation": None, "aligned": None}
  corr = float(a.iloc[-n:].corr(b.iloc[-n:]))
  return {"available": True, "correlation": round(corr, 3), "window": n, "high_beta": abs(corr) > 0.7}


def orderbook_imbalance(exchange, symbol: str, depth: int = 20) -> dict:
  """Bid/ask volume imbalance from order book (-1 to +1)."""
  try:
    book = exchange.fetch_order_book(symbol, limit=depth)
    bids = sum(b[1] for b in book.get("bids", [])[:depth])
    asks = sum(a[1] for a in book.get("asks", [])[:depth])
    total = bids + asks
    if total <= 0:
      return {"available": False, "imbalance": 0.0}
    imb = (bids - asks) / total
    return {"available": True, "imbalance": round(imb, 3), "bid_vol": bids, "ask_vol": asks}
  except Exception as e:
    return {"available": False, "error": str(e), "imbalance": 0.0}


def funding_rate_snapshot(exchange, symbol: str) -> dict:
  """Perpetual funding rate if available."""
  try:
    if not exchange.has.get("fetchFundingRate"):
      return {"available": False}
    perp = symbol.replace("/USDT", "/USDT:USDT")
    fr = exchange.fetch_funding_rate(perp)
    rate = float(fr.get("fundingRate") or 0)
    return {
      "available": True,
      "rate": rate,
      "rate_pct": round(rate * 100, 4),
      "bias": "long_pays" if rate > 0 else "short_pays" if rate < 0 else "neutral",
    }
  except Exception:
    return {"available": False}


def build_market_confluence(
  symbol: str,
  data: Dict[str, pd.DataFrame],
  tfs: List[str],
  btc_1d: Optional[pd.DataFrame] = None,
  exchange=None,
) -> dict:
  """Aggregate supplementary tools (EW remains primary)."""
  primary_tf = "1h" if "1h" in data else "1d"
  df_p = data.get(primary_tf)
  if df_p is None:
    df_p = data.get("1d")
  raw = compute_raw_indicators(df_p) if df_p is not None and len(df_p) >= 20 else {}

  tools: Dict[str, Any] = {
    "vwap_dist_pct": vwap_distance_pct(df_p) if df_p is not None else 0,
    "rsi_divergence": detect_rsi_divergence(df_p) if df_p is not None else None,
    "multi_tf_rsi": multi_tf_rsi_stack(data, tfs),
    "btc_correlation": btc_correlation(symbol, data.get("1d", df_p), btc_1d),
    "raw_indicators": raw,
  }

  # TV OSS indicators (Supertrend, Bollinger, ADX)
  if df_p is not None and len(df_p) >= 30:
    from core.tv_indicators import compute_tv_signals, score_tv_confluence

    tools["tv_signals"] = compute_tv_signals(df_p)
    tools["tv_confluence"] = score_tv_confluence(df_p, "LONG")  # default; per-setup scored in outcomes
  else:
    tools["tv_signals"] = {"available": False}
    tools["tv_confluence"] = {"score": 0, "aligned": False, "signals": []}

  if exchange is not None:
    tools["orderbook"] = orderbook_imbalance(exchange, symbol)
    tools["funding"] = funding_rate_snapshot(exchange, symbol)
  else:
    tools["orderbook"] = {"available": False}
    tools["funding"] = {"available": False}

  # Confluence score boost for readiness (0-20)
  boost = 0
  signals: List[str] = []
  rsi_stack = tools["multi_tf_rsi"]
  if rsi_stack.get("bias") == "BULL":
    boost += 5
    signals.append(f"RSI stack bullish ({rsi_stack.get('bull_count')} TFs)")
  elif rsi_stack.get("bias") == "BEAR":
    boost += 5
    signals.append(f"RSI stack bearish ({rsi_stack.get('bear_count')} TFs)")

  div = tools.get("rsi_divergence")
  if div:
    boost += 8
    signals.append(div)

  ob = tools.get("orderbook", {})
  if ob.get("available"):
    imb = ob.get("imbalance", 0)
    if abs(imb) > 0.15:
      boost += 5
      signals.append(f"orderbook imb {imb:+.2f}")

  fr = tools.get("funding", {})
  if fr.get("available") and abs(fr.get("rate", 0)) > 0.0001:
    signals.append(f"funding {fr.get('rate_pct')}% ({fr.get('bias')})")

  tv = tools.get("tv_signals", {})
  if tv.get("supertrend", {}).get("available"):
    st = tv["supertrend"]
    signals.append(f"supertrend {st.get('signal')}")
  if tv.get("adx", {}).get("trend") == "strong":
    boost += 5
    signals.append(f"ADX {tv['adx'].get('adx', 0):.0f} strong trend")

  tools["confluence_boost"] = min(boost, 20)
  tools["confluence_signals"] = signals
  return tools
