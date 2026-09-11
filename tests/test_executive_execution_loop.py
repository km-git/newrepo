"""Tests for OOS field population and executive export filtering."""

from __future__ import annotations

import pandas as pd

from engine.autodream import enrich_outcomes_with_autodream
from engine.executive_board import (
  filter_rows_by_executive_action,
  stamp_executive_on_export_rows,
  TRADABLE_EXECUTIVE_ACTIONS,
)
from engine.execution_agent import filter_by_executive_action


def _sample_df():
  idx = pd.date_range("2024-01-01", periods=80, freq="D")
  return pd.DataFrame({
    "Open": range(80),
    "High": range(1, 81),
    "Low": range(80),
    "Close": range(80),
    "Volume": [1000] * 80,
  }, index=idx)


def test_enrich_outcomes_sets_oos_fields():
  df = _sample_df()
  outcomes = {
    "setups": {
      "swing": {"status": "executable", "risk": {}, "targets": [{"price": 1}]},
    },
  }
  enriched = enrich_outcomes_with_autodream(outcomes, "BTC/USDT", {"1d": df})
  setup = enriched["setups"]["swing"]
  assert "oos_win_rate" in setup
  assert "oos_trades" in setup
  assert setup["oos_gate"] in ("passed", "below_threshold", "insufficient_oos")


def test_stamp_executive_on_export_rows():
  board = {
    "picks": [
      {
        "symbol": "BTC/USDT",
        "style": "swing",
        "timeframe": "1d",
        "executive_action": "EXECUTE_NOW",
        "executive_score": 82,
        "position_size_pct": 100,
        "playbook": "go",
      },
    ],
  }
  rows = [
    {"symbol": "BTC/USDT", "timeframe": "1d", "gtc_tier": "executable"},
    {"symbol": "ETH/USDT", "timeframe": "1h", "gtc_tier": "executable"},
  ]
  stamped = stamp_executive_on_export_rows(rows, board)
  assert stamped[0]["executive_action"] == "EXECUTE_NOW"
  assert stamped[0]["executive_score"] == 82
  assert stamped[1]["executive_action"] == "WATCH_ONLY"


def test_filter_rows_by_executive_action():
  rows = [
    {"executive_action": "EXECUTE_NOW"},
    {"executive_action": "WATCH_ONLY"},
    {"executive_action": "STANDBY_LIMIT"},
  ]
  filtered = filter_rows_by_executive_action(rows)
  actions = {r["executive_action"] for r in filtered}
  assert "WATCH_ONLY" not in actions
  assert actions <= set(TRADABLE_EXECUTIVE_ACTIONS)


def test_execution_agent_filter_by_executive_action(monkeypatch):
  monkeypatch.delenv("EW_EXECUTIVE_FILTER", raising=False)
  rows = [
    {"executive_action": "EXECUTE_CAUTION", "gtc_tier": "executable", "row_type": "primary"},
    {"executive_action": "WATCH_ONLY", "gtc_tier": "executable", "row_type": "primary"},
  ]
  filtered = filter_by_executive_action(rows)
  assert len(filtered) == 1
  assert filtered[0]["executive_action"] == "EXECUTE_CAUTION"
