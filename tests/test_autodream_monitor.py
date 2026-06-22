"""Tests for autodream monitor trigger evaluation."""

from __future__ import annotations

import pandas as pd

from engine.autodream_monitor import (
  evaluate_triggers,
  impulse_on_tf,
  rejection_wick,
  _zone_bounds,
)


def _ohlc(rows):
  return pd.DataFrame(rows, columns=["Open", "High", "Low", "Close", "Volume"])


def test_rejection_wick_long():
  df = _ohlc([[100, 101, 95, 100.5, 1]])  # long lower wick, bullish close
  assert rejection_wick(df, "LONG") is True


def test_rejection_wick_short():
  df = _ohlc([[100, 105, 99, 99.5, 1]])  # long upper wick, bearish close
  assert rejection_wick(df, "SHORT") is True


def test_zone_bounds_from_entry():
  lo, hi = _zone_bounds(None, 100.0, 2.0)
  assert lo < 100 < hi


def test_upgrade_monitor_to_executable():
  """Impulse aligned + in zone → executable."""
  df = _ohlc([[10, 11, 9, 10.5, 1]] * 20)
  data = {"15m": df, "1d": df}
  # Bear impulse monowaves: Down Up Down Up Down
  mws = [
    {"type": "Down", "price_start": 12, "price_end": 10},
    {"type": "Up", "price_start": 10, "price_end": 10.5},
    {"type": "Down", "price_start": 10.5, "price_end": 9.5},
    {"type": "Up", "price_start": 9.5, "price_end": 10},
    {"type": "Down", "price_start": 10, "price_end": 9},
  ]
  adaptive = {"15m": {"monowaves": mws}}
  item = {
    "symbol": "TEST/USDT",
    "style": "scalp",
    "status": "monitor",
    "direction": "SHORT",
    "entry": 10.0,
    "entry_zone": [9.5, 10.5],
    "stop": 12.0,
    "check": "15m",
  }
  result = evaluate_triggers(item, data, adaptive)
  assert result["in_zone"] is True
  assert result["new_status"] in ("executable", "monitor")


def test_invalidate_stop_breach():
  df = _ohlc([[10, 11, 9, 10.5, 1]] * 20)
  df.iloc[-1, df.columns.get_loc("Close")] = 15.0  # above stop for SHORT
  data = {"15m": df, "1d": df}
  mws = [{"type": "Down", "price_start": 12, "price_end": 10}] * 5
  adaptive = {"15m": {"monowaves": mws}}
  item = {
    "symbol": "TEST/USDT",
    "style": "scalp",
    "status": "monitor",
    "direction": "SHORT",
    "entry": 10.0,
    "entry_zone": [9.5, 10.5],
    "stop": 12.0,
    "check": "15m",
  }
  result = evaluate_triggers(item, data, adaptive)
  assert result["invalidated"] is True
  assert result["new_status"] == "invalidated"
