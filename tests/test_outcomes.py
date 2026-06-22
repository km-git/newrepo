"""Tests for outcome-driven setups and dynamic DCA."""

from __future__ import annotations

import pandas as pd

from core.risk import build_dca_ladder, dynamic_stop, dynamic_targets
from engine.autodream import _get_df, enrich_outcomes_with_autodream


def test_dca_splits_10_20_30_40():
  legs = build_dca_ladder("LONG", 100.0, 2.0, 95.0, 105.0)
  assert [l["size_pct"] for l in legs] == [10, 20, 30, 40]
  assert legs[0]["price"] == 100.0
  assert legs[3]["price"] <= 95.0


def test_dynamic_stop_long():
  s = dynamic_stop("LONG", 100.0, 2.0, 96.0, 110.0, atr_mult=1.0)
  assert s["price"] < 96.0


def test_dynamic_targets_three_tiers():
  t = dynamic_targets("LONG", 100.0, 2.0)
  assert len(t) == 3
  assert t[0]["exit_pct"] == 40
  assert t[0]["price"] > 100.0


def test_get_df_avoids_dataframe_truthiness():
  df = pd.DataFrame({"Close": [1.0, 2.0], "High": [1.5, 2.5], "Low": [0.5, 1.5]})
  data = {"15m": df}
  assert _get_df(data, "15m") is df
  assert _get_df(data, "1h", "15m") is df


def test_enrich_outcomes_with_autodream():
  idx = pd.date_range("2024-01-01", periods=80, freq="D")
  df = pd.DataFrame({
    "Open": range(80),
    "High": range(1, 81),
    "Low": range(80),
    "Close": range(80),
    "Volume": [1000] * 80,
  }, index=idx)
  outcomes = {
    "setups": {
      "scalp": {"status": "monitor", "risk": {}, "targets": [{"price": 1}, {"rr": 1.5}]},
    },
  }
  enriched = enrich_outcomes_with_autodream(outcomes, "TEST/USDT", {"1d": df, "15m": df})
  assert "autodream" in enriched
  assert enriched["autodream"]["by_style"]["scalp"]["available"] is True
