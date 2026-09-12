"""Sentinel Trader-style multi-processor fusion adapter.

There is no official Sentinel Trader EW API; this module implements the same
fusion pattern used by sentinel-style terminals: structure + momentum + cycle +
VWAP/volume processors voting into one directional score.

Optional: if `wave-alpha` is installed (`pip install wave-alpha`), a supplementary
EW thesis vote is included.
"""

from __future__ import annotations

from typing import Any, Dict, List, Optional

import numpy as np
import pandas as pd

from cache.disk_cache import get_cache
from core.ehlers import ehlers_cycle_bias, ehlers_instantaneous_phase
from core.market_tools import vwap_distance_pct
from core.wave_alpha_adapter import scan_wave_alpha

TF_WEIGHTS = {"1w": 2.0, "1d": 2.5, "4h": 1.5, "1h": 1.2, "15m": 1.0}


def _try_wave_alpha(symbol: str) -> Optional[dict]:
  """wave-alpha EW thesis vote (requires pip install wave-alpha)."""
  return scan_wave_alpha(symbol)


def _momentum_sentinel(df: pd.DataFrame) -> dict:
  if df is None or len(df) < 50:
    return {"available": False}
  close = df["Close"].astype(float)
  ema20 = close.ewm(span=20, adjust=False).mean()
  ema50 = close.ewm(span=50, adjust=False).mean()
  roc10 = (close.iloc[-1] / close.iloc[-11] - 1) * 100 if len(close) > 11 else 0
  price = float(close.iloc[-1])
  e20, e50 = float(ema20.iloc[-1]), float(ema50.iloc[-1])
  bull_pts = bear_pts = 0
  if price > e20:
    bull_pts += 1
  if e20 > e50:
    bull_pts += 1
  if roc10 > 0:
    bull_pts += 1
  if price < e20:
    bear_pts += 1
  if e20 < e50:
    bear_pts += 1
  if roc10 < 0:
    bear_pts += 1
  if bull_pts > bear_pts:
    return {"available": True, "direction": "BULL", "score": bull_pts / 3, "detail": f"momentum roc={roc10:.2f}%"}
  if bear_pts > bull_pts:
    return {"available": True, "direction": "BEAR", "score": bear_pts / 3, "detail": f"momentum roc={roc10:.2f}%"}
  return {"available": True, "direction": "NEUTRAL", "score": 0.5, "detail": "momentum flat"}


def _structure_sentinel(wave_structure: dict, consensus: dict) -> dict:
  bull = bear = 0.0
  for tf, w in wave_structure.items():
    wt = TF_WEIGHTS.get(tf, 1.0)
    d = w.get("direction", "n/a")
    if d == "BULL":
      bull += wt
    elif d == "BEAR":
      bear += wt
  c_dir = (consensus or {}).get("consensus_direction", "NEUTRAL")
  if c_dir == "BULL":
    bull += 2
  elif c_dir == "BEAR":
    bear += 2
  total = bull + bear
  if total == 0:
    return {"available": False}
  if bull >= bear:
    return {"available": True, "direction": "BULL", "score": bull / total, "detail": f"structure {bull:.1f}/{total:.1f} bull"}
  return {"available": True, "direction": "BEAR", "score": bear / total, "detail": f"structure {bear:.1f}/{total:.1f} bear"}


def _cycle_sentinel(df: pd.DataFrame, cycle_confluence: dict) -> dict:
  if df is None or len(df) < 40:
    cc = cycle_confluence or {}
    d = cc.get("cycle_direction", "NEUTRAL")
    return {"available": d in ("BULL", "BEAR"), "direction": d, "score": cc.get("cycle_confidence", 0.5), "detail": "cycle aggregate"}
  close = df["Close"].astype(float).to_numpy()
  hurst = (cycle_confluence or {}).get("primary_hurst", 0.5) or 0.5
  bias, detail = ehlers_cycle_bias(close, hurst=float(hurst))
  ph = ehlers_instantaneous_phase(close)
  return {
    "available": True,
    "direction": bias,
    "score": 0.65 if ph.get("trend_mode") else 0.55,
    "detail": detail,
    "ehlers_phase_deg": ph.get("phase_deg"),
    "ehlers_phase_label": ph.get("phase_label"),
  }


def _vwap_sentinel(df: pd.DataFrame) -> dict:
  if df is None or len(df) < 10:
    return {"available": False}
  dist = vwap_distance_pct(df)
  if dist > 0.3:
    return {"available": True, "direction": "BULL", "score": min(abs(dist) / 3, 1), "detail": f"above VWAP {dist:+.2f}%"}
  if dist < -0.3:
    return {"available": True, "direction": "BEAR", "score": min(abs(dist) / 3, 1), "detail": f"below VWAP {dist:+.2f}%"}
  return {"available": True, "direction": "NEUTRAL", "score": 0.4, "detail": f"VWAP flat {dist:+.2f}%"}


def build_sentinel_analysis(
  symbol: str,
  data: Dict[str, pd.DataFrame],
  wave_structure: dict,
  cycle_confluence: dict,
  market_tools: Optional[dict] = None,
  consensus: Optional[dict] = None,
) -> dict:
  """
  Sentinel Trader-style processor fusion → single directional vote.
  Cached per symbol + bar counts.
  """
  cache = get_cache()
  tfs = tuple(sorted(data.keys()))

  def _compute():
    df_1d = data.get("1d")
    if df_1d is None:
      df_1d = data.get("4h")
    if df_1d is None and data:
      df_1d = next(iter(data.values()))
    processors: Dict[str, dict] = {
      "momentum": _momentum_sentinel(df_1d),
      "structure": _structure_sentinel(wave_structure, consensus or {}),
      "cycle": _cycle_sentinel(df_1d, cycle_confluence or {}),
      "vwap": _vwap_sentinel(df_1d),
    }

    mkt = market_tools or {}
    rsi = mkt.get("multi_tf_rsi", {})
    if rsi.get("bias") in ("BULL", "BEAR"):
      processors["rsi_stack"] = {
        "available": True,
        "direction": rsi["bias"],
        "score": 0.6,
        "detail": f"RSI stack {rsi['bias']}",
      }

    wa = _try_wave_alpha(symbol)
    if wa and wa.get("available"):
      processors["wave_alpha"] = {
        "available": True,
        "direction": wa["direction"],
        "score": wa.get("confidence", 0.7),
        "detail": wa.get("detail", "wave-alpha"),
        "pattern": wa.get("pattern"),
        "ticker": wa.get("ticker"),
      }

    weights = {
      "structure": 3.0,
      "cycle": 2.5,
      "momentum": 2.0,
      "vwap": 1.5,
      "rsi_stack": 1.2,
      "wave_alpha": 2.8,
    }

    bull = bear = 0.0
    signals: List[str] = []
    for name, proc in processors.items():
      if not proc.get("available"):
        continue
      d = proc.get("direction", "NEUTRAL")
      w = weights.get(name, 1.0) * proc.get("score", 0.5)
      signals.append(f"{name}:{proc.get('detail', d)}")
      if d == "BULL":
        bull += w
      elif d == "BEAR":
        bear += w

    total = bull + bear
    if total == 0:
      direction, confidence = "BULL", 0.4
    elif bull >= bear:
      direction = "BULL"
      confidence = round(bull / total, 3)
    else:
      direction = "BEAR"
      confidence = round(bear / total, 3)

    return {
      "available": True,
      "source": "sentinel_adapter",
      "direction": direction,
      "confidence": confidence,
      "processors": processors,
      "signals": signals[:8],
      "bull_weight": round(bull, 2),
      "bear_weight": round(bear, 2),
      "wave_alpha_installed": bool(wa and wa.get("available")),
      "wave_alpha_ticker": (wa or {}).get("ticker"),
    }

  result, hit = cache.get_or_compute(
    "sentinel_analysis",
    _compute,
    symbol,
    tfs,
    *(len(data[k]) for k in data),
  )
  result["cache_hit"] = hit
  return result
