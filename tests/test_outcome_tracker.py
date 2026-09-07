"""Tests for historical outcome tracking and feedback loop."""

from __future__ import annotations

import json
from pathlib import Path

import pytest

from engine.outcome_tracker import (
  TRACKED_PATH,
  METRICS_PATH,
  apply_feedback_to_row,
  compute_metrics,
  feedback_for_row,
  record_setups,
  resolve_open_setups,
  simulate_forward,
  setup_key,
)


def test_simulate_forward_long_tp_wins():
  highs = [101, 102, 103]
  lows = [99, 100, 101]
  assert simulate_forward("LONG", 100, 95, 102, highs, lows) == "tp1_hit"


def test_simulate_forward_long_sl_first():
  highs = [100.5, 101, 102]
  lows = [99, 94, 98]
  assert simulate_forward("LONG", 100, 95, 110, highs, lows) == "sl_hit"


def test_simulate_forward_short_tp_wins():
  highs = [101, 100, 99]
  lows = [99, 98, 97]
  assert simulate_forward("SHORT", 100, 105, 98, highs, lows) == "tp1_hit"


def test_record_setups_dedupes_open(tmp_path: Path, monkeypatch):
  monkeypatch.setattr("engine.outcome_tracker.TRACKED_PATH", tmp_path / "tracked.json")
  rows = [
    {
      "row_type": "primary",
      "symbol": "BTC/USDT",
      "timeframe": "1h",
      "direction": "SHORT",
      "gtc_tier": "executable",
      "honest_execution_tier": "probe",
      "wae": 100,
      "stop_loss": 110,
      "tp1": 90,
    },
  ]
  assert record_setups(rows) == 1
  assert record_setups(rows) == 0


def test_skips_fixture_symbols_and_resolves_invalid(tmp_path: Path, monkeypatch):
  monkeypatch.setattr("engine.outcome_tracker.TRACKED_PATH", tmp_path / "tracked.json")
  assert record_setups([
    {
      "row_type": "primary",
      "symbol": "B/USDT",
      "timeframe": "1h",
      "direction": "LONG",
      "gtc_tier": "executable",
      "wae": 1,
      "stop_loss": 0.9,
      "tp1": 1.1,
    },
  ]) == 0
  tmp_path.joinpath("tracked.json").write_text(
    json.dumps({
      "open": [{
        "id": "B/USDT|1h|LONG",
        "symbol": "B/USDT",
        "timeframe": "1h",
        "direction": "LONG",
        "wae": 1,
        "stop_loss": 0.9,
        "tp1": 1.1,
        "recorded_at": "2026-01-01T00:00:00+00:00",
        "status": "open",
      }],
      "closed": [],
    }),
    encoding="utf-8",
  )
  assert resolve_open_setups(is_crypto=True) == 1
  state = json.loads(tmp_path.joinpath("tracked.json").read_text())
  assert state["open"] == []
  assert state["closed"][0]["status"] == "invalid_symbol"


def test_feedback_downgrades_poor_history():
  metrics = {
    "by_pair_tf": {
      setup_key("BTC/USDT", "1h", "SHORT"): {
        "n": 5, "wins": 1, "losses": 4, "decided": 5, "win_rate": 0.2,
      },
    },
    "by_timeframe": {},
    "overall": {},
  }
  row = {
    "symbol": "BTC/USDT",
    "timeframe": "1h",
    "direction": "SHORT",
    "gtc_tier": "executable",
    "honest_execution_tier": "probe",
    "gtc_size_cap_pct": 50,
  }
  out = apply_feedback_to_row(row, metrics)
  assert out["gtc_tier"] == "monitor"
  assert out["gtc_size_cap_pct"] == 37.5
  assert out["hist_action"] == "downgrade"
  assert out["hist_scope"] == "pair_tf"


def test_feedback_boosts_strong_history():
  metrics = {
    "by_pair_tf": {
      setup_key("ETH/USDT", "15m", "LONG"): {
        "n": 6, "wins": 5, "losses": 1, "decided": 6, "win_rate": 0.833,
      },
    },
    "by_timeframe": {},
    "overall": {},
  }
  row = {
    "symbol": "ETH/USDT",
    "timeframe": "15m",
    "direction": "LONG",
    "gtc_tier": "executable",
    "honest_execution_tier": "full",
    "gtc_size_cap_pct": 100,
    "wae": 100,
    "stop_loss": 95,
    "tp1": 110,
  }
  out = apply_feedback_to_row(row, metrics)
  assert out["gtc_tier"] == "executable"
  assert out["gtc_size_cap_pct"] == 100.0
  assert out["hist_action"] == "boost"
  assert out["hist_scope"] == "pair_tf"


def test_feedback_labels_aggregate_history_as_context_only():
  metrics = {
    "by_pair_tf": {},
    "by_timeframe": {
      "15m": {"decided": 100, "win_rate": 0.70},
    },
    "overall": {"decided": 200, "win_rate": 0.62},
  }
  row = {
    "symbol": "NEW/USDT",
    "timeframe": "15m",
    "direction": "SHORT",
    "gtc_tier": "monitor",
  }
  out = apply_feedback_to_row(row, metrics)
  assert out["hist_win_rate"] == 0.70
  assert out["hist_n"] == 100
  assert out["hist_scope"] == "timeframe"


def test_compute_metrics_dedupes_by_setup_id(tmp_path: Path, monkeypatch):
  monkeypatch.setattr("engine.outcome_tracker.TRACKED_PATH", tmp_path / "tracked.json")
  state = {
    "open": [],
    "closed": [
      {"id": "BTC/USDT|1h|LONG", "symbol": "BTC/USDT", "timeframe": "1h", "direction": "LONG",
       "status": "sl_hit", "resolved_at": "2024-01-01T00:00:00+00:00"},
      {"id": "BTC/USDT|1h|LONG", "symbol": "BTC/USDT", "timeframe": "1h", "direction": "LONG",
       "status": "tp1_hit", "resolved_at": "2024-02-01T00:00:00+00:00"},
    ],
  }
  (tmp_path / "tracked.json").write_text(json.dumps(state))
  m = compute_metrics()
  assert m["overall"]["decided"] == 1
  assert m["overall"]["wins"] == 1


def test_compute_metrics_from_closed(tmp_path: Path, monkeypatch):
  monkeypatch.setattr("engine.outcome_tracker.TRACKED_PATH", tmp_path / "tracked.json")
  state = {
    "open": [],
    "closed": [
      {"id": "A/USDT|1h|LONG", "symbol": "A/USDT", "timeframe": "1h", "direction": "LONG",
       "status": "tp1_hit", "resolved_at": "2024-01-02T00:00:00+00:00",
       "gtc_tier": "executable", "honest_execution_tier": "probe"},
      {"id": "B/USDT|1h|LONG", "symbol": "B/USDT", "timeframe": "1h", "direction": "LONG",
       "status": "sl_hit", "resolved_at": "2024-01-01T00:00:00+00:00",
       "gtc_tier": "executable", "honest_execution_tier": "probe"},
    ],
  }
  (tmp_path / "tracked.json").write_text(json.dumps(state))
  m = compute_metrics()
  assert m["overall"]["wins"] == 1
  assert m["overall"]["losses"] == 1
  assert m["overall"]["win_rate"] == 0.5
