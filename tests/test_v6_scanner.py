"""Tests for V6 config and best-trade ranking."""

from __future__ import annotations

from engine.best_trades import rank_executable_setups, score_setup
from engine.v6_config import V6_TIMEFRAMES, active_timeframes, v6_enabled


def test_v6_timeframes_count():
  assert len(V6_TIMEFRAMES) == 6
  assert "12h" in V6_TIMEFRAMES


def test_active_timeframes_v6(monkeypatch):
  monkeypatch.setenv("EW_V6_SETUP", "1")
  tfs = active_timeframes()
  assert len(tfs) == 6
  assert "12h" in tfs


def test_active_timeframes_legacy(monkeypatch):
  monkeypatch.setenv("EW_V6_SETUP", "0")
  tfs = active_timeframes()
  assert len(tfs) == 5
  assert "12h" not in tfs


def test_score_executable_row():
  row = {
    "gtc_tier": "executable",
    "wae": 80,
    "readiness_score": 70,
    "rr_tp2": 2.5,
    "honest_execution_tier": "full",
    "row_type": "primary",
  }
  assert score_setup(row) > 0


def test_rank_executable_filters_monitor():
  rows = [
    {"row_type": "primary", "gtc_tier": "monitor", "wae": 90},
    {"row_type": "primary", "gtc_tier": "executable", "wae": 50, "readiness_score": 60, "rr_tp2": 2},
  ]
  ranked = rank_executable_setups(rows, limit=10)
  assert len(ranked) == 1
  assert ranked[0]["wae"] == "50" or ranked[0]["wae"] == 50
