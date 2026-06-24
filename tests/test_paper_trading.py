"""Tests for paper trading and setup-faithful historical simulation."""

from __future__ import annotations

import pandas as pd

from engine.paper_trading import (
  apply_honesty_adjustments,
  backtest_setup_on_bars,
  honesty_verdict,
  paper_trade_setup,
  run_paper_batch,
)
from engine.trade_simulation import forward_bars_after_entry, simulate_forward


def _ohlc(n: int, start: float = 100.0, step: float = 0.5):
  rows = []
  px = start
  for _ in range(n):
    rows.append([px, px + 1, px - 1, px + step, 1.0])
    px += step
  return pd.DataFrame(rows, columns=["Open", "High", "Low", "Close", "Volume"])


def test_simulate_forward_long_win():
  highs = [101, 102, 103, 104, 105]
  lows = [99, 100, 101, 102, 103]
  targets = [
    {"price": 102, "exit_pct": 40, "rr": 2.0, "label": "TP1"},
    {"price": 104, "exit_pct": 60, "rr": 4.0, "label": "TP2"},
  ]
  r = simulate_forward(highs, lows, entry=100, stop=98, targets=targets, direction="LONG", max_bars=5)
  assert r["outcome"] == "win"
  assert r["pnl_r"] > 0


def test_simulate_forward_short_loss():
  highs = [101, 102, 103, 104, 105]
  lows = [99, 100, 101, 102, 103]
  targets = [{"price": 95, "exit_pct": 100, "rr": 5.0, "label": "TP1"}]
  r = simulate_forward(highs, lows, entry=100, stop=102, targets=targets, direction="SHORT", max_bars=5)
  assert r["outcome"] == "loss"
  assert r["pnl_r"] < 0


def test_backtest_setup_on_bars():
  df = _ohlc(80, start=50, step=0.2)
  setup = {
    "style": "swing",
    "direction": "LONG",
    "entry": {"anchor": 60.0, "zone": [58.0, 62.0]},
    "stop_loss": {"price": 55.0},
    "targets": [
      {"price": 65.0, "exit_pct": 40, "rr": 1.5},
      {"price": 70.0, "exit_pct": 30, "rr": 3.0},
      {"price": 75.0, "exit_pct": 30, "rr": 5.0},
    ],
    "zone_dist_pct": 5.0,
  }
  r = backtest_setup_on_bars(df, setup, lookback_bars=40)
  assert r["available"] is True
  assert r["method"] == "setup_faithful_zone_entries"


def test_paper_trade_setup_probe_size():
  df = _ohlc(30)
  setup = {
    "style": "scalp",
    "status": "executable",
    "execution_tier": "probe",
    "direction": "LONG",
    "entry": {"anchor": float(df["Close"].iloc[-2])},
    "stop_loss": {"price": float(df["Close"].iloc[-2]) - 2},
    "targets": [{"price": float(df["Close"].iloc[-2]) + 3, "exit_pct": 100, "rr": 1.5}],
  }
  r = paper_trade_setup("TEST/USDT", setup, df)
  assert r["available"] is True
  assert r["size_factor"] == 0.35


def test_forward_bars_after_entry_skips_entry_bar():
  highs = [100, 101, 102, 103]
  lows = [99, 100, 101, 102]
  fh, fl = forward_bars_after_entry(highs, lows, entry_bar_idx=2, max_bars=10)
  assert fh == [103]
  assert fl == [102]


def test_paper_trade_no_same_bar_stop():
  """Entry bar wick through stop must not count — sim starts bar+1."""
  rows = []
  for i in range(10):
    rows.append([100, 101, 90, 100.5, 1.0])  # bar 8 would stop long if included
  rows.append([100, 101, 99, 100.0, 1.0])
  rows.append([100, 101, 99, 100.0, 1.0])
  df = pd.DataFrame(rows, columns=["Open", "High", "Low", "Close", "Volume"])
  setup = {
    "style": "scalp",
    "status": "executable",
    "execution_tier": "full",
    "direction": "LONG",
    "entry": {"anchor": 100.0},
    "stop_loss": {"price": 95.0},
    "targets": [{"price": 110.0, "exit_pct": 100, "rr": 2.0}],
  }
  r = paper_trade_setup("TEST/USDT", setup, df)
  assert r["available"] is True
  assert r["paper_outcome"] != "loss" or r.get("bars_held", 0) != 1 or "stop@1" not in r.get("exit_detail", "")


def test_run_paper_batch_executable_only():
  from engine.paper_trading import run_paper_batch
  import engine.paper_trading as pt

  df = _ohlc(40)
  results = [{
    "symbol": "TEST/USDT",
    "status": "complete",
    "step8_outcomes": {
      "setups": {
        "scalp": {
          "status": "monitor",
          "execution_tier": "none",
          "direction": "LONG",
          "entry": {"anchor": 100},
          "stop_loss": {"price": 98},
          "targets": [{"price": 105, "exit_pct": 100, "rr": 2.5}],
        },
        "day_trade": {
          "status": "executable",
          "execution_tier": "probe",
          "direction": "LONG",
          "entry": {"anchor": float(df["Close"].iloc[-2])},
          "stop_loss": {"price": float(df["Close"].iloc[-2]) - 2},
          "targets": [{"price": float(df["Close"].iloc[-2]) + 4, "exit_pct": 100, "rr": 2.0}],
        },
      }
    },
  }]

  def fake_fetch(sym, tfs, is_crypto=True):
    return {"15m": df, "1h": df, "1d": df, "4h": df, "1w": df}

  orig = pt._fetch_symbol_data
  pt._fetch_symbol_data = fake_fetch
  try:
    report = run_paper_batch(results, fetch_missing=True, executable_only=True)
  finally:
    pt._fetch_symbol_data = orig

  assert report["monitor_skipped"] == 1
  assert report["setups_papered"] == 1
  assert report["paper_policy"] == "executable_only"
  assert report["trades"][0]["style"] == "day_trade"


def test_honesty_verdict_caution():
  assert honesty_verdict(0.35, 10, "probe") == "caution"
  assert honesty_verdict(0.60, 10, "full") == "validated"
  assert honesty_verdict(None, 1, "probe") == "insufficient_data"
  assert honesty_verdict(0.70, 20, "probe", oos_win_rate=0.30, oos_trades=10) == "caution"
  assert honesty_verdict(0.70, 20, "full", oos_win_rate=0.60, oos_trades=10, wf_degradation=0.25) == "caution"


def test_apply_honesty_boosts_readiness():
  outcomes = {
    "setups": {
      "swing": {
        "status": "executable",
        "execution_tier": "full",
        "readiness_score": 70,
        "historical_edge": 0.62,
        "hist_trades": 8,
        "oos_win_rate": 0.62,
        "oos_trades": 12,
        "honest_reason": "swing FULL",
      }
    }
  }
  out = apply_honesty_adjustments(outcomes)
  assert out["setups"]["swing"]["readiness_score"] > 70
  assert out["setups"]["swing"]["autodream_verdict"] == "validated"
  assert out["setups"]["swing"]["oos_gate"] == "passed"
