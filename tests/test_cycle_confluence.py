"""Tests for Hurst cycle confluence and expert direction resolver."""

from __future__ import annotations

import numpy as np
import pandas as pd

from core.cycle_confluence import (
  build_cycle_confluence,
  cycle_phase_direction,
  dominant_cycle_period,
  hurst_rs_exponent,
)
from core.direction_resolver import build_sentinel_stack, resolve_expert_direction


def _trend_df(n: int = 200, drift: float = 0.002) -> pd.DataFrame:
  rng = np.random.default_rng(7)
  close = 100 * np.exp(np.cumsum(rng.normal(drift, 0.01, n)))
  return pd.DataFrame({
    "Open": close * 0.999,
    "High": close * 1.005,
    "Low": close * 0.995,
    "Close": close,
    "Volume": 1e6,
  })


def test_hurst_on_trending_series():
  close = _trend_df(300, drift=0.003)["Close"].to_numpy()
  h = hurst_rs_exponent(close)
  assert 0.0 <= h <= 1.0


def test_dominant_cycle_finds_period():
  close = _trend_df(256)["Close"].to_numpy()
  period, power = dominant_cycle_period(close, min_period=10, max_period=80)
  assert period >= 0
  if period > 0:
    assert power > 0


def test_cycle_phase_returns_bias():
  close = _trend_df(120)["Close"].to_numpy()
  phase, label, bias = cycle_phase_direction(close, period=20, hurst=0.55)
  assert 0 <= phase <= 360
  assert label in ("rising_leg", "falling_leg", "peak_zone", "trough_zone", "unknown")
  assert bias in ("BULL", "BEAR", "NEUTRAL")


def test_build_cycle_confluence():
  data = {"1d": _trend_df(180), "4h": _trend_df(180)}
  result = build_cycle_confluence("TEST/USDT", data, ["1d", "4h"])
  assert "cycle_direction" in result
  assert result["cycle_direction"] in ("BULL", "BEAR", "NEUTRAL")
  assert "by_tf" in result


def _wave_matrix_bull():
  base = {
    "structure": "bull_impulse_5",
    "direction": "BULL",
    "impulse_valid": True,
    "waves_last5": [{"type": "Up"}],
    "abc": None,
    "diagonal": None,
  }
  return {tf: dict(base, tf=tf) for tf in ["1w", "1d", "4h", "1h", "15m"]}


def test_resolve_expert_direction_always_clear():
  adaptive = {
    "1d": {"monowaves": [{"type": "Up", "price_start": 1, "price_end": 2}]},
  }
  expert = resolve_expert_direction(
    wave_structure=_wave_matrix_bull(),
    adaptive=adaptive,
    htf_class={"bias": "bullish_reversal", "state": "corrective"},
    consensus={"consensus_direction": "BULL", "consensus_score": 0.7, "agreement_pct": 80},
    cycle_confluence={"cycle_direction": "BULL", "cycle_confidence": 0.7, "primary_regime": "trending"},
    harmonic_overlaps=[],
    exec_direction="BULL",
    execution_passes=False,
    market_tools={"multi_tf_rsi": {"bias": "BULL"}},
  )
  assert expert["direction"] in ("BULL", "BEAR")
  assert expert["confidence"] > 0
  assert "honest_note" in expert


def test_sentinel_stack_weights_htf_and_consensus():
  bear_wave = {
    "structure": "bear_impulse_5",
    "direction": "BEAR",
    "impulse_valid": True,
    "waves_last5": [{"type": "Down"}],
    "abc": None,
    "diagonal": None,
  }
  bear_matrix = {tf: dict(bear_wave, tf=tf) for tf in ["1w", "1d", "4h", "1h", "15m"]}
  sentinel = build_sentinel_stack(
    wave_structure=bear_matrix,
    adaptive={},
    htf_class={"bias": "bearish_impulse"},
    consensus={"consensus_direction": "BEAR", "consensus_score": 0.6},
    cycle_confluence={"cycle_direction": "BEAR", "cycle_confidence": 0.6},
    harmonic_overlaps=[{"bullish": False}],
    market_tools={},
  )
  assert sentinel["direction"] == "BEAR"
  assert sentinel["bear_weight"] > sentinel["bull_weight"]
