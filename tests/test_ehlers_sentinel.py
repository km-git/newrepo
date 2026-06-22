"""Tests for Ehlers Hilbert and Sentinel Trader adapter."""

from __future__ import annotations

import numpy as np
import pandas as pd

from core.ehlers import ehlers_cycle_bias, ehlers_instantaneous_phase
from core.sentinel_adapter import build_sentinel_analysis


def _sine_trend_df(n: int = 200, period: int = 40) -> pd.DataFrame:
  t = np.arange(n)
  close = 100 + 5 * np.sin(2 * np.pi * t / period) + 0.02 * t
  return pd.DataFrame({
    "Open": close,
    "High": close * 1.002,
    "Low": close * 0.998,
    "Close": close,
    "Volume": 1e6,
  })


def test_ehlers_instantaneous_phase():
  close = _sine_trend_df(180)["Close"].to_numpy()
  ph = ehlers_instantaneous_phase(close, hp_period=48)
  assert ph["available"]
  assert 0 <= ph["phase_deg"] <= 360
  assert ph["phase_label"] in ("rising_leg", "falling_leg", "peak_zone", "trough_zone")


def test_ehlers_cycle_bias_clear():
  close = _sine_trend_df(200)["Close"].to_numpy()
  bias, detail = ehlers_cycle_bias(close, hurst=0.55)
  assert bias in ("BULL", "BEAR", "NEUTRAL")
  assert "Ehlers" in detail


def test_sentinel_analysis_fusion():
  df = _sine_trend_df(150)
  wave = {
    "1d": {"direction": "BULL", "structure": "bull_impulse_5", "impulse_valid": True},
    "4h": {"direction": "BULL", "structure": "abc_correction", "impulse_valid": False},
  }
  cycle = {"cycle_direction": "BULL", "cycle_confidence": 0.6, "primary_hurst": 0.55}
  result = build_sentinel_analysis(
    "TEST/USDT",
    {"1d": df, "4h": df},
    wave,
    cycle,
    market_tools={"multi_tf_rsi": {"bias": "BULL"}},
    consensus={"consensus_direction": "BULL"},
  )
  assert result["available"]
  assert result["direction"] in ("BULL", "BEAR")
  assert "processors" in result
  assert "momentum" in result["processors"]
