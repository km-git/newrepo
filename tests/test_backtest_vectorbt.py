"""Tests for optional vectorbt backtest adapter."""

from __future__ import annotations

import numpy as np
import pandas as pd

from engine.backtest_vectorbt import backtest_setup_vectorbt, vectorbt_available


def _df(n=80):
  close = 100 + np.cumsum(np.random.default_rng(1).normal(0, 0.2, n))
  return pd.DataFrame({
    "Open": close,
    "High": close + 0.5,
    "Low": close - 0.5,
    "Close": close,
    "Volume": np.ones(n) * 1000,
  })


def test_vectorbt_graceful_without_package():
  r = backtest_setup_vectorbt(_df(), {
    "style": "smc",
    "direction": "LONG",
    "entry": {"anchor": 100},
    "stop_loss": {"price": 98},
    "targets": [{"price": 101}, {"price": 104, "rr": 2}],
  })
  if not vectorbt_available():
    assert r.get("available") is False
  else:
    assert "available" in r
