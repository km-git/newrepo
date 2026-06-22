"""Hurst cycles + dominant-cycle phase analysis — supplementary EW confluence."""

from __future__ import annotations

from typing import Any, Dict, List, Optional, Tuple

import numpy as np
import pandas as pd

from cache.disk_cache import get_cache

TF_WEIGHTS = {"1w": 2.5, "1d": 2.0, "4h": 1.5, "1h": 1.2, "15m": 1.0}


def hurst_rs_exponent(series: np.ndarray, min_lag: int = 8, max_lag: int = 64) -> float:
  """Rescaled-range Hurst exponent on log returns."""
  if len(series) < max_lag * 2:
    return 0.5
  log_ret = np.diff(np.log(np.maximum(series.astype(float), 1e-12)))
  if len(log_ret) < max_lag * 2:
    return 0.5

  lags: List[int] = []
  rs_vals: List[float] = []
  for lag in range(min_lag, min(max_lag, len(log_ret) // 2)):
    chunks = len(log_ret) // lag
    if chunks < 2:
      continue
    rs_chunk: List[float] = []
    for i in range(chunks):
      seg = log_ret[i * lag : (i + 1) * lag]
      mean = seg.mean()
      dev = np.cumsum(seg - mean)
      r = dev.max() - dev.min()
      s = seg.std(ddof=1)
      if s > 1e-12:
        rs_chunk.append(r / s)
    if rs_chunk:
      lags.append(lag)
      rs_vals.append(float(np.mean(rs_chunk)))

  if len(lags) < 3:
    return 0.5
  slope, _ = np.polyfit(np.log(lags), np.log(np.maximum(rs_vals, 1e-12)), 1)
  return float(np.clip(slope, 0.0, 1.0))


def dominant_cycle_period(close: np.ndarray, min_period: int = 8, max_period: int = 120) -> Tuple[int, float]:
  """Dominant cycle length (bars) via FFT on detrended log price."""
  n = len(close)
  if n < max_period * 2:
    return 0, 0.0
  x = np.log(np.maximum(close.astype(float), 1e-12))
  x = x - np.linspace(x[0], x[-1], n)
  spec = np.abs(np.fft.rfft(x))
  freqs = np.fft.rfftfreq(n, d=1.0)
  best_p, best_pwr = 0, 0.0
  for f, pwr in zip(freqs[1:], spec[1:]):
    if f <= 0:
      continue
    period = int(round(1.0 / f))
    if min_period <= period <= max_period and pwr > best_pwr:
      best_p, best_pwr = period, float(pwr)
  return best_p, best_pwr


def cycle_phase_direction(
  close: np.ndarray,
  period: int,
  hurst: float,
) -> Tuple[float, str, str]:
  """
  Estimate cycle phase (0–360°) and directional bias from phase + Hurst regime.
  Returns (phase_deg, phase_label, cycle_bias BULL/BEAR/NEUTRAL).
  """
  if period < 8 or len(close) < period * 2:
    return 0.0, "unknown", "NEUTRAL"

  x = close.astype(float)
  ma = pd.Series(x).rolling(period, min_periods=period // 2).mean().to_numpy()
  det = x - np.nan_to_num(ma, nan=x.mean())
  # Hilbert-like phase proxy: correlation with sin/cos at dominant period
  t = np.arange(len(det))
  sin_c = np.sin(2 * np.pi * t / period)
  cos_c = np.cos(2 * np.pi * t / period)
  sin_corr = float(np.corrcoef(det[-period * 2 :], sin_c[-period * 2 :])[0, 1])
  cos_corr = float(np.corrcoef(det[-period * 2 :], cos_c[-period * 2 :])[0, 1])
  phase_rad = np.arctan2(sin_corr, cos_corr)
  phase_deg = float((np.degrees(phase_rad) + 360) % 360)

  if 45 <= phase_deg < 135:
    label = "rising_leg"
  elif 135 <= phase_deg < 225:
    label = "peak_zone"
  elif 225 <= phase_deg < 315:
    label = "falling_leg"
  else:
    label = "trough_zone"

  # Hurst regime: persistent → follow cycle leg; mean-reverting → fade extremes
  if hurst >= 0.52:
    if label in ("rising_leg", "trough_zone"):
      bias = "BULL"
    elif label in ("falling_leg", "peak_zone"):
      bias = "BEAR"
    else:
      bias = "NEUTRAL"
  elif hurst <= 0.48:
    if label in ("peak_zone",):
      bias = "BEAR"
    elif label in ("trough_zone",):
      bias = "BULL"
    elif label == "rising_leg":
      bias = "BULL"
    else:
      bias = "BEAR"
  else:
    bias = "BULL" if label in ("rising_leg", "trough_zone") else "BEAR"

  return round(phase_deg, 1), label, bias


def analyze_tf_cycles(df: pd.DataFrame, tf: str) -> dict:
  if df is None or len(df) < 40:
    return {"tf": tf, "available": False, "reason": "insufficient_bars"}

  close = df["Close"].astype(float).to_numpy()
  hurst = hurst_rs_exponent(close)
  period, power = dominant_cycle_period(close)
  phase_deg, phase_label, cycle_bias = cycle_phase_direction(close, period, hurst)

  regime = "trending" if hurst >= 0.52 else "mean_reverting" if hurst <= 0.48 else "random"

  return {
    "tf": tf,
    "available": True,
    "hurst": round(hurst, 3),
    "regime": regime,
    "dominant_period_bars": period,
    "cycle_power": round(power, 4),
    "phase_deg": phase_deg,
    "phase_label": phase_label,
    "cycle_bias": cycle_bias,
    "detail": f"H={hurst:.2f} P={period}b {phase_label} ({regime})",
  }


def build_cycle_confluence(
  symbol: str,
  data: Dict[str, pd.DataFrame],
  tfs: Optional[List[str]] = None,
) -> dict:
  """Aggregate Hurst + dominant-cycle analysis across timeframes."""
  tfs = tfs or ["1w", "1d", "4h", "1h", "15m"]
  cache = get_cache()

  def _compute():
    by_tf: Dict[str, dict] = {}
    for tf in tfs:
      if tf in data:
        by_tf[tf] = analyze_tf_cycles(data[tf], tf)
      else:
        by_tf[tf] = {"tf": tf, "available": False, "reason": "missing"}

    bull_w = bear_w = 0.0
    signals: List[str] = []
    for tf, info in by_tf.items():
      if not info.get("available"):
        continue
      w = TF_WEIGHTS.get(tf, 1.0)
      bias = info.get("cycle_bias", "NEUTRAL")
      if bias == "BULL":
        bull_w += w
      elif bias == "BEAR":
        bear_w += w
      signals.append(f"{tf}:{info.get('detail', '')}")

    total = bull_w + bear_w
    if total == 0:
      cycle_direction = "NEUTRAL"
      confidence = 0.0
    elif bull_w > bear_w:
      cycle_direction = "BULL"
      confidence = round(bull_w / total, 3)
    else:
      cycle_direction = "BEAR"
      confidence = round(bear_w / total, 3)

    primary = by_tf.get("1d") or by_tf.get("4h") or next(
      (v for v in by_tf.values() if v.get("available")), {}
    )

    boost = 0
    if confidence >= 0.65:
      boost += 10
    elif confidence >= 0.55:
      boost += 6
    if primary.get("regime") == "trending":
      boost += 4
      signals.append(f"hurst trending H={primary.get('hurst')}")

    return {
      "by_tf": by_tf,
      "cycle_direction": cycle_direction,
      "cycle_confidence": confidence,
      "primary_hurst": primary.get("hurst"),
      "primary_period": primary.get("dominant_period_bars"),
      "primary_phase": primary.get("phase_label"),
      "primary_regime": primary.get("regime"),
      "confluence_boost": min(boost, 15),
      "confluence_signals": signals[:6],
    }

  result, hit = cache.get_or_compute(
    "hurst_cycles",
    _compute,
    symbol,
    tuple(tfs),
    *(len(data[tf]) for tf in tfs if tf in data),
  )
  result["cache_hit"] = hit
  return result
