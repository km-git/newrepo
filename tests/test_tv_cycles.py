"""Tests for Hurst cycle and fractal regime indicators."""

from __future__ import annotations

import numpy as np
import pandas as pd


def _trend_df(n=120):
  close = np.linspace(100, 130, n) + np.random.default_rng(1).normal(0, 0.5, n)
  return pd.DataFrame({
    "Open": close,
    "High": close + 1,
    "Low": close - 1,
    "Close": close,
    "Volume": np.full(n, 10000.0),
  })


def test_hurst_trending():
  from core.tv_cycles import hurst_exponent

  r = hurst_exponent(_trend_df()["Close"])
  assert r["available"] is True
  assert 0 <= r["hurst"] <= 1


def test_dominant_cycle():
  from core.tv_cycles import dominant_cycle_period

  # Sine-like cycle (need len >= max_period * 2)
  t = np.arange(130)
  close = 100 + 5 * np.sin(2 * np.pi * t / 20)
  r = dominant_cycle_period(pd.Series(close))
  assert r["available"] is True
  assert r["period"] > 0


def test_cycle_bundle():
  from core.tv_cycles import compute_cycle_signals, score_cycle_confluence

  cy = compute_cycle_signals(_trend_df())
  assert cy["available"] is True
  assert cy["hurst"]["available"]
  score = score_cycle_confluence(cy, "LONG")
  assert "strategy_mode" in score


def test_tv_signals_include_cycles():
  from core.tv_indicators import compute_tv_signals

  sig = compute_tv_signals(_trend_df())
  assert "cycles" in sig
  assert sig["cycles"].get("available")
