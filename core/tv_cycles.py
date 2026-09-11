"""
TradingView-style cycle & fractal indicators (OSS logic).

Hurst exponent, dominant cycle, cycle phase, fractal dimension — regime
detectors that can completely change strategy selection (trend vs mean-revert).
"""

from __future__ import annotations

from typing import Any, Dict, List, Optional, Tuple

import numpy as np
import pandas as pd


TV_CYCLE_CATALOG: Tuple[Dict[str, str], ...] = (
  {"id": "hurst", "role": "regime", "desc": "Hurst exponent — trending vs mean-reverting regime"},
  {"id": "dominant_cycle", "role": "cycle", "desc": "Dominant cycle period via autocorrelation"},
  {"id": "cycle_phase", "role": "cycle", "desc": "Cycle phase — early/mid/late in wave"},
  {"id": "fractal_dim", "role": "regime", "desc": "Fractal dimension — market complexity"},
  {"id": "autocorr_cycle", "role": "cycle", "desc": "Autocorrelation cycle strength"},
  {"id": "ehlers_roofing", "role": "cycle", "desc": "Ehlers roofing filter — cycle isolation"},
)


def _log_returns(close: pd.Series) -> pd.Series:
  c = close.astype(float).replace(0, np.nan)
  return np.log(c / c.shift(1)).dropna()


def hurst_exponent(close: pd.Series, max_lag: int = 20) -> Dict[str, Any]:
  """
  Hurst exponent via R/S analysis (classic TV OSS / Mandelbrot).
  H > 0.55 → persistent/trending | H < 0.45 → anti-persistent/mean-revert
  """
  if close is None or len(close) < max_lag * 3:
    return {"available": False, "hurst": 0.5, "signal": "neutral"}

  series = close.astype(float).dropna().values
  lags = range(2, max_lag + 1)
  rs_vals = []
  for lag in lags:
    chunks = [series[i : i + lag] for i in range(0, len(series) - lag, lag)]
    if len(chunks) < 2:
      continue
    rs_list = []
    for chunk in chunks:
      if len(chunk) < 2:
        continue
      mean = chunk.mean()
      dev = np.cumsum(chunk - mean)
      r = dev.max() - dev.min()
      s = chunk.std(ddof=1)
      if s > 0:
        rs_list.append(r / s)
    if rs_list:
      rs_vals.append((np.log(lag), np.log(np.mean(rs_list))))

  if len(rs_vals) < 3:
    return {"available": False, "hurst": 0.5, "signal": "neutral"}

  x = np.array([v[0] for v in rs_vals])
  y = np.array([v[1] for v in rs_vals])
  h = float(np.polyfit(x, y, 1)[0])
  h = max(0.0, min(1.0, h))

  if h >= 0.58:
    signal = "persistent_trend"
  elif h >= 0.52:
    signal = "weak_trend"
  elif h <= 0.42:
    signal = "mean_reverting"
  elif h <= 0.48:
    signal = "weak_mean_revert"
  else:
    signal = "random_walk"

  return {
    "available": True,
    "hurst": round(h, 4),
    "signal": signal,
    "regime": "trend" if h > 0.52 else "mean_revert" if h < 0.48 else "neutral",
  }


def dominant_cycle_period(close: pd.Series, min_period: int = 5, max_period: int = 60) -> Dict[str, Any]:
  """Find dominant cycle length via autocorrelation peak."""
  if close is None or len(close) < max_period * 2:
    return {"available": False, "period": 0, "signal": "neutral"}

  c = close.astype(float).values
  c = c - c.mean()
  n = len(c)
  corr = []
  for lag in range(min_period, max_period + 1):
    if lag >= n:
      break
    num = np.sum(c[: n - lag] * c[lag:])
    den = np.sqrt(np.sum(c[: n - lag] ** 2) * np.sum(c[lag:] ** 2))
    corr.append((lag, num / den if den > 0 else 0))

  if not corr:
    return {"available": False, "period": 0, "signal": "neutral"}

  best_lag, best_corr = max(corr, key=lambda x: x[1])
  strength = abs(best_corr)

  if strength > 0.35:
    signal = "strong_cycle"
  elif strength > 0.20:
    signal = "moderate_cycle"
  else:
    signal = "no_clear_cycle"

  return {
    "available": True,
    "period": int(best_lag),
    "correlation": round(float(best_corr), 4),
    "strength": round(strength, 4),
    "signal": signal,
  }


def cycle_phase(close: pd.Series, period: int = 20) -> Dict[str, Any]:
  """Estimate position in dominant cycle (0–100%)."""
  if close is None or len(close) < period * 2:
    return {"available": False, "phase_pct": 50, "signal": "neutral"}

  c = close.astype(float)
  # Hilbert-like proxy: detrended oscillator position in band
  ma = c.rolling(period).mean()
  detrended = c - ma
  band = detrended.rolling(period).std().replace(0, np.nan)
  norm = (detrended / band).iloc[-1]
  if not np.isfinite(norm):
    return {"available": False, "phase_pct": 50, "signal": "neutral"}

  # Map oscillator to phase
  phase = int((np.arctan(norm) / np.pi + 0.5) * 100)
  phase = max(0, min(100, phase))

  if phase < 25:
    signal = "cycle_trough"
  elif phase < 50:
    signal = "cycle_rising"
  elif phase < 75:
    signal = "cycle_peak_zone"
  else:
    signal = "cycle_falling"

  return {"available": True, "phase_pct": phase, "signal": signal, "period": period}


def fractal_dimension(close: pd.Series, k_max: int = 8) -> Dict[str, Any]:
  """
  Fractal dimension via Higuchi method (simplified).
  Low D → smoother/trending | High D → noisy/choppy
  """
  if close is None or len(close) < k_max * 10:
    return {"available": False, "fractal_dim": 1.5, "signal": "neutral"}

  x = close.astype(float).values
  n = len(x)
  lk = []
  for k in range(1, k_max + 1):
    lm = []
    for m in range(k):
      idx = np.arange(m, n - 1, k)
      if len(idx) < 2:
        continue
      lm.append(np.sum(np.abs(np.diff(x[idx]))) * (n - 1) / (len(idx) * k))
    if lm:
      lk.append((np.log(1.0 / k), np.log(np.mean(lm))))

  if len(lk) < 3:
    return {"available": False, "fractal_dim": 1.5, "signal": "neutral"}

  xs = np.array([p[0] for p in lk])
  ys = np.array([p[1] for p in lk])
  fd = float(np.polyfit(xs, ys, 1)[0])

  if fd < 1.3:
    signal = "smooth_trend"
  elif fd > 1.7:
    signal = "choppy_noise"
  else:
    signal = "normal"

  return {"available": True, "fractal_dim": round(fd, 4), "signal": signal}


def ehlers_roofing_filter(close: pd.Series, hp_period: int = 48) -> Dict[str, Any]:
  """Ehlers roofing filter — isolate cycle component (popular TV OSS)."""
  if close is None or len(close) < hp_period + 10:
    return {"available": False, "signal": "neutral"}

  c = close.astype(float).values
  # Simple high-pass = price - SMA (roofing approximation)
  sma = pd.Series(c).rolling(hp_period).mean().values
  cycle = c - sma
  val = float(cycle[-1])
  prev = float(cycle[-3]) if len(cycle) > 3 else val
  slope = val - prev

  if val > 0 and slope > 0:
    signal = "cycle_up"
  elif val < 0 and slope < 0:
    signal = "cycle_down"
  elif val > 0:
    signal = "cycle_top"
  else:
    signal = "cycle_bottom"

  return {"available": True, "cycle_value": round(val, 6), "slope": round(slope, 6), "signal": signal}


def compute_cycle_signals(df: pd.DataFrame) -> Dict[str, Any]:
  """Bundle Hurst + cycle + fractal indicators."""
  if df is None or len(df) < 60:
    return {"available": False, "reason": "insufficient_bars"}

  close = df["Close"]
  dom = dominant_cycle_period(close)
  period = dom.get("period") or 20

  return {
    "available": True,
    "hurst": hurst_exponent(close),
    "dominant_cycle": dom,
    "cycle_phase": cycle_phase(close, period=max(10, min(period, 40))),
    "fractal_dim": fractal_dimension(close),
    "ehlers_roofing": ehlers_roofing_filter(close),
    "catalog": [c["id"] for c in TV_CYCLE_CATALOG],
  }


def score_cycle_confluence(cycles: Dict[str, Any], direction: str) -> Dict[str, Any]:
  """
  Score cycle/regime alignment — game-changer for strategy mode selection.
  Trend setups need H>0.52; mean-revert setups need H<0.48.
  """
  if not cycles.get("available"):
    return {"score": 50, "aligned": False, "signals": [], "strategy_mode": "neutral"}

  is_long = direction.upper() in ("LONG", "BULL")
  score = 30
  notes: List[str] = []

  h = cycles.get("hurst") or {}
  if h.get("available"):
    hv = h.get("hurst", 0.5)
    regime = h.get("regime", "neutral")
    notes.append(f"Hurst {hv:.2f} ({h.get('signal')})")
    if regime == "trend":
      score += 15
      notes.append("trend regime — favor impulse/EW continuation")
    elif regime == "mean_revert":
      score += 8
      notes.append("mean-revert regime — favor PRZ bounces, tighten targets")
    else:
      score -= 5
      notes.append("random-walk regime — reduce size")

  dom = cycles.get("dominant_cycle") or {}
  if dom.get("available") and dom.get("signal") != "no_clear_cycle":
    score += 10
    notes.append(f"dominant cycle {dom.get('period')} bars (r={dom.get('correlation')})")

  ph = cycles.get("cycle_phase") or {}
  if ph.get("available"):
    sig = ph.get("signal", "")
    if is_long and sig in ("cycle_trough", "cycle_rising"):
      score += 12
      notes.append(f"cycle phase {ph.get('phase_pct')}% — long favorable")
    elif not is_long and sig in ("cycle_peak_zone", "cycle_falling"):
      score += 12
      notes.append(f"cycle phase {ph.get('phase_pct')}% — short favorable")
    elif sig in ("cycle_trough", "cycle_peak_zone"):
      score -= 8
      notes.append(f"cycle phase opposes ({sig})")

  roof = cycles.get("ehlers_roofing") or {}
  if roof.get("available"):
    if (is_long and roof["signal"] in ("cycle_up", "cycle_bottom")) or (
      not is_long and roof["signal"] in ("cycle_down", "cycle_top")
    ):
      score += 8
      notes.append(f"Ehlers roofing {roof['signal']}")

  fd = cycles.get("fractal_dim") or {}
  if fd.get("available") and fd.get("signal") == "choppy_noise":
    score -= 10
    notes.append("high fractal dim — choppy, avoid probes")

  score = max(0, min(100, score))
  strategy_mode = "trend" if (h.get("hurst") or 0.5) > 0.52 else "mean_revert" if (h.get("hurst") or 0.5) < 0.48 else "balanced"

  return {
    "score": score,
    "aligned": score >= 55,
    "signals": notes,
    "strategy_mode": strategy_mode,
    "raw": cycles,
  }
