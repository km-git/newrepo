"""Tests for walk-forward, holdout, Monte Carlo, and stress validation."""

from __future__ import annotations

import pandas as pd

from engine.backtest_strategies import (
  anchored_walk_forward,
  collect_zone_trades,
  holdout_analysis,
  monte_carlo_bootstrap,
  perturbation_stress_test,
  run_all_validation,
  walk_forward_analysis,
)


def _ohlc(n: int, start: float = 100.0, step: float = 0.3):
  rows = []
  px = start
  for _ in range(n):
    rows.append([px, px + 1.5, px - 1.5, px + step, 1.0])
    px += step
  return pd.DataFrame(rows, columns=["Open", "High", "Low", "Close", "Volume"])


def _setup():
  return {
    "style": "day_trade",
    "direction": "LONG",
    "entry": {"anchor": 110.0, "zone": [105.0, 115.0]},
    "stop_loss": {"price": 100.0},
    "targets": [
      {"price": 115.0, "exit_pct": 40, "rr": 1.5},
      {"price": 120.0, "exit_pct": 30, "rr": 3.0},
      {"price": 125.0, "exit_pct": 30, "rr": 5.0},
    ],
    "zone_dist_pct": 5.0,
  }


def test_collect_zone_trades():
  df = _ohlc(120)
  trades = collect_zone_trades(df, _setup(), lookback_bars=80)
  assert isinstance(trades, list)


def test_walk_forward_analysis():
  df = _ohlc(150)
  r = walk_forward_analysis(df, _setup(), n_folds=4, lookback_bars=100)
  assert r.get("available") is True
  assert r["method"] == "walk_forward"
  assert len(r["folds"]) == 4
  assert "oos_win_rate" in r


def test_holdout_analysis():
  df = _ohlc(150)
  r = holdout_analysis(df, _setup(), lookback_bars=100)
  assert r.get("available") is True
  assert r["method"] == "holdout"
  assert "in_sample" in r and "out_of_sample" in r


def test_monte_carlo_bootstrap():
  trades = [
    {"outcome": "win", "pnl_r": 1.5},
    {"outcome": "loss", "pnl_r": -1.0},
    {"outcome": "win", "pnl_r": 2.0},
    {"outcome": "win", "pnl_r": 0.8},
    {"outcome": "loss", "pnl_r": -1.0},
  ]
  r = monte_carlo_bootstrap(trades, n_runs=200, seed=1)
  assert r["available"] is True
  assert r["win_rate_p5"] <= r["win_rate_median"] <= r["win_rate_p95"]


def test_perturbation_stress_test():
  df = _ohlc(100)
  r = perturbation_stress_test(df, _setup(), lookback_bars=60)
  assert r.get("available") is True
  assert "base" in r and "stressed" in r


def test_anchored_walk_forward():
  df = _ohlc(150)
  r = anchored_walk_forward(df, _setup(), n_folds=3, lookback_bars=100)
  assert r.get("available") is True
  assert r["method"] == "anchored_walk_forward"


def test_run_all_validation():
  df = _ohlc(150)
  r = run_all_validation(df, _setup(), lookback_bars=80)
  assert "walk_forward" in r
  assert "holdout" in r
  assert "monte_carlo" in r
  assert "stress" in r
