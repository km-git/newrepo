"""Expectancy-driven execution gate tests."""

from __future__ import annotations

import json
from pathlib import Path

from engine.execution_gates import _stop_distance_ok, blocked_timeframes, gate_row


def test_stop_distance_gate(monkeypatch):
  monkeypatch.setenv("EW_MIN_STOP_PCT", "0.02")
  ok, reason = _stop_distance_ok({"wae": 100, "stop_loss": 99.5})
  assert not ok
  assert reason and "stop_too_tight" in reason


def test_expectancy_blocks_timeframe(monkeypatch, tmp_path):
  monkeypatch.setenv("EW_EXPECTANCY_STATE", str(tmp_path / "exp.json"))
  monkeypatch.setenv("EW_EXPECTANCY_GATES", "1")
  tmp_path.joinpath("exp.json").write_text(json.dumps({
    "blocked_slices": {"timeframe": ["4h"], "direction": [], "pair_tf": []},
  }))
  assert "4h" in blocked_timeframes()


def test_gate_row_blocks_weak_tf(monkeypatch):
  monkeypatch.setenv("EW_REGIME_GATES", "1")
  monkeypatch.setenv("EW_BLOCKED_TFS", "4h")
  row = {
    "row_type": "primary",
    "gtc_tier": "executable",
    "timeframe": "4h",
    "direction": "LONG",
    "wae": 100,
    "stop_loss": 90,
    "gtc_size_cap_pct": 50,
    "honest_execution_tier": "probe",
  }
  ok, reasons = gate_row(row)
  assert not ok
  assert any("tf_blocked" in r or "4h" in r for r in reasons)
