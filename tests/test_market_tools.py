"""Tests for supplementary market tools."""

from __future__ import annotations

import pandas as pd

from core.market_tools import multi_tf_rsi_stack, vwap_distance_pct


def _df(n=50):
  return pd.DataFrame({
    "Open": range(n),
    "High": range(1, n + 1),
    "Low": range(n),
    "Close": range(n),
    "Volume": [1000] * n,
  })


def test_vwap_distance():
  d = vwap_distance_pct(_df())
  assert isinstance(d, float)


def test_multi_tf_rsi():
  data = {"1d": _df(), "4h": _df()}
  r = multi_tf_rsi_stack(data, ["1d", "4h", "15m"])
  assert r["bias"] in ("BULL", "BEAR", "NEUTRAL")
  assert r["by_tf"]["15m"] is None
