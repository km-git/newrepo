"""Tests for walk-forward backtest runner."""

from __future__ import annotations

from engine.backtest_runner import run_walk_forward_backtest


def test_backtest_no_rows_returns_fitness(monkeypatch, tmp_path):
  monkeypatch.chdir(tmp_path)
  result = run_walk_forward_backtest(fetch_ohlc=False)
  assert result["ok"] is False
  assert result["reason"] == "no_export_rows"
  assert "fitness" in result
