"""Tests for SMC structure and TV edge layer."""

from __future__ import annotations

import numpy as np
import pandas as pd

from core.smc_structure import analyze_smc, smc_aligns_direction
from core.tv_enhanced import compute_enhanced_indicators, detect_oscillator_divergence
from engine.tv_edge import build_tv_edge_layer


def _ohlcv(n: int = 120, trend: float = 0.001) -> pd.DataFrame:
  rng = np.random.default_rng(42)
  close = 100 + np.cumsum(rng.normal(trend, 0.5, n))
  high = close + rng.uniform(0.1, 0.8, n)
  low = close - rng.uniform(0.1, 0.8, n)
  open_ = np.roll(close, 1)
  open_[0] = close[0]
  return pd.DataFrame({
    "Open": open_, "High": high, "Low": low, "Close": close,
    "Volume": rng.uniform(1000, 5000, n),
  })


def test_analyze_smc_returns_structure():
  df = _ohlcv(150)
  smc = analyze_smc(df)
  assert smc["status"] == "ok"
  assert "smc_score" in smc
  assert "structure_bias" in smc


def test_smc_aligns_direction():
  smc = {"status": "ok", "structure_bias": "BULL", "in_bull_ob": True}
  assert smc_aligns_direction(smc, "LONG")
  assert not smc_aligns_direction(smc, "SHORT")


def test_enhanced_indicators():
  df = _ohlcv(80)
  enh = compute_enhanced_indicators(df)
  assert enh["status"] in ("ok", "fallback")


def test_tv_edge_layer():
  data = {"1h": _ohlcv(120), "4h": _ohlcv(120), "1d": _ohlcv(120)}
  edge = build_tv_edge_layer("BTC/USDT", data, "LONG", primary_tf="1h")
  assert "edge_score" in edge
  assert "smc_matrix" in edge
  assert "tags" in edge
