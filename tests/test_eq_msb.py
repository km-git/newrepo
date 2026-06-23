"""Tests for EQ liquidity and MSB z-score modules."""

from __future__ import annotations

import numpy as np
import pandas as pd

from core.eq_liquidity import detect_equal_levels, detect_eq_sweep
from core.msb_zscore import validate_msb_zscore


def _ohlcv(n: int = 120) -> pd.DataFrame:
  rng = np.random.default_rng(3)
  close = 100 + np.cumsum(rng.normal(0, 0.3, n))
  idx = pd.date_range("2025-01-01", periods=n, freq="1h", tz="UTC")
  return pd.DataFrame({
    "Open": close - rng.uniform(0, 0.1, n),
    "High": close + rng.uniform(0.1, 0.4, n),
    "Low": close - rng.uniform(0.1, 0.4, n),
    "Close": close,
    "Volume": rng.uniform(1000, 5000, n),
  }, index=idx)


def test_detect_equal_levels():
  r = detect_equal_levels(_ohlcv(100))
  assert r.get("status") == "ok"
  assert "eq_highs" in r
  assert "eq_lows" in r


def test_detect_eq_sweep_returns_optional():
  r = detect_eq_sweep(_ohlcv(100), "LONG")
  assert r is None or "level" in r


def test_msb_zscore_runs():
  r = validate_msb_zscore(_ohlcv(80), "LONG")
  assert r.get("status") in ("ok", "no_break", "insufficient_data")
  assert "pass" in r
