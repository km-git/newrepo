"""John Ehlers DSP — Hilbert transform, instantaneous phase, cycle mode."""

from __future__ import annotations

from typing import Tuple

import numpy as np


def _ehlers_highpass(close: np.ndarray, period: float = 48.0) -> np.ndarray:
  """Ehlers 2-pole high-pass filter removes trend for cycle measurement."""
  if len(close) < 10:
    return close.astype(float) - close.astype(float).mean()

  alpha = (np.cos(0.707 * 2 * np.pi / period) + np.sin(0.707 * 2 * np.pi / period) - 1) / np.cos(
    0.707 * 2 * np.pi / period
  )
  hp = np.zeros(len(close))
  x = close.astype(float)
  for i in range(2, len(x)):
    hp[i] = (
      (1 - alpha / 2) ** 2 * (x[i] - 2 * x[i - 1] + x[i - 2])
      + 2 * (1 - alpha) * hp[i - 1]
      - (1 - alpha) ** 2 * hp[i - 2]
    )
  return hp


def _hilbert_analytic(x: np.ndarray) -> np.ndarray:
  """FFT Hilbert transform — analytic signal (real + j*imag)."""
  n = len(x)
  if n < 8:
    return x.astype(complex)
  spec = np.fft.fft(x.astype(float))
  h = np.zeros(n)
  if n % 2 == 0:
    h[0] = 1.0
    h[n // 2] = 1.0
    h[1 : n // 2] = 2.0
  else:
    h[0] = 1.0
    h[1 : (n + 1) // 2] = 2.0
  return np.fft.ifft(spec * h)


def ehlers_instantaneous_phase(
  close: np.ndarray,
  hp_period: float = 48.0,
) -> dict:
  """
  Ehlers-style instantaneous phase on detrended price.
  Returns phase_deg (0–360), phase_label, phase_velocity, in_phase_component.
  """
  if len(close) < 32:
    return {
      "available": False,
      "phase_deg": 0.0,
      "phase_label": "unknown",
      "phase_velocity": 0.0,
      "trend_mode": False,
    }

  hp = _ehlers_highpass(close, period=hp_period)
  analytic = _hilbert_analytic(hp)
  real = np.real(analytic)
  imag = np.imag(analytic)

  # Avoid divide-by-zero at phase wraps
  phase = np.arctan2(imag, real)
  phase_deg = float((np.degrees(phase[-1]) + 360) % 360)

  # Phase velocity (degrees per bar) — turning point detection
  if len(phase) >= 5:
    dphase = np.degrees(np.diff(phase[-5:]))
    # unwrap jumps
    dphase = np.where(dphase > 180, dphase - 360, dphase)
    dphase = np.where(dphase < -180, dphase + 360, dphase)
    phase_velocity = float(np.mean(dphase))
  else:
    phase_velocity = 0.0

  # Trend mode: Ehlers Homodyne — low phase variance = trending
  phase_var = float(np.var(np.degrees(phase[-20:]))) if len(phase) >= 20 else 999.0
  trend_mode = phase_var < 120.0

  if 30 <= phase_deg < 150:
    label = "rising_leg"
  elif 150 <= phase_deg < 210:
    label = "peak_zone"
  elif 210 <= phase_deg < 330:
    label = "falling_leg"
  else:
    label = "trough_zone"

  return {
    "available": True,
    "phase_deg": round(phase_deg, 1),
    "phase_label": label,
    "phase_velocity": round(phase_velocity, 2),
    "trend_mode": trend_mode,
    "phase_variance": round(phase_var, 1),
    "in_phase": round(float(real[-1]), 6),
    "quadrature": round(float(imag[-1]), 6),
  }


def ehlers_cycle_bias(
  close: np.ndarray,
  hurst: float,
  hp_period: float = 48.0,
) -> Tuple[str, str]:
  """
  Directional bias from Ehlers phase + Hurst regime.
  Returns (bias BULL/BEAR, detail string).
  """
  ph = ehlers_instantaneous_phase(close, hp_period=hp_period)
  if not ph.get("available"):
    return "NEUTRAL", "ehlers_unavailable"

  label = ph["phase_label"]
  vel = ph["phase_velocity"]
  trend = ph["trend_mode"]

  if trend and hurst >= 0.5:
    # Trending: follow phase leg + velocity
    if label in ("rising_leg", "trough_zone") or vel > 2:
      bias = "BULL"
    elif label in ("falling_leg", "peak_zone") or vel < -2:
      bias = "BEAR"
    else:
      bias = "BULL" if vel >= 0 else "BEAR"
  elif hurst <= 0.48:
    # Mean revert at extremes
    if label == "peak_zone":
      bias = "BEAR"
    elif label == "trough_zone":
      bias = "BULL"
    else:
      bias = "BULL" if vel > 0 else "BEAR"
  else:
    bias = "BULL" if label in ("rising_leg", "trough_zone") else "BEAR"

  detail = (
    f"Ehlers {label} {ph['phase_deg']}° vel={vel:+.1f} "
    f"{'trend' if trend else 'cycle'}"
  )
  return bias, detail
