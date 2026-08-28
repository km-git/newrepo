"""Tests for fee-adjusted walk-forward validation."""

from __future__ import annotations

import json
from pathlib import Path

import pytest


@pytest.fixture
def wf_fixture_state(tmp_path):
  closed = []
  for i in range(120):
    closed.append({
      "id": f"TEST/USDT|1h|SHORT|{i}",
      "symbol": "TEST/USDT",
      "timeframe": "1h",
      "direction": "SHORT",
      "wae": 100.0,
      "stop_loss": 102.0,
      "tp1": 97.0,
      "tp1_exit_pct": 50,
      "status": "tp1_hit" if i % 4 != 0 else "sl_hit",
      "resolved_at": f"2026-02-{(i % 28) + 1:02d}T12:00:00+00:00",
    })
  path = tmp_path / "tracked.json"
  path.write_text(json.dumps({"open": [], "closed": closed}), encoding="utf-8")
  return path


def test_net_r_from_setup_fee_drag():
  from engine.walk_forward_validator import net_r_from_setup

  win = net_r_from_setup({
    "status": "tp1_hit",
    "wae": 100.0,
    "stop_loss": 98.0,
    "tp1": 103.0,
    "tp1_exit_pct": 50,
  })
  loss = net_r_from_setup({
    "status": "sl_hit",
    "wae": 100.0,
    "stop_loss": 98.0,
    "tp1": 103.0,
  })
  assert win is not None and loss is not None
  assert loss < -1.0
  assert win < 1.5


def test_run_fee_walk_forward_1h(monkeypatch, wf_fixture_state):
  monkeypatch.setenv("EW_DIRECTION_GATES", "0")
  monkeypatch.setenv("EW_REGIME_GATES", "0")
  import engine.outcome_tracker as ot

  ot.TRACKED_PATH = wf_fixture_state
  from engine.walk_forward_validator import run_fee_walk_forward

  result = run_fee_walk_forward(timeframe="1h", apply_policy=False)
  assert result.get("ok") is True
  assert result.get("gate_passed") is True
  assert result.get("expectancy_r") is not None
  assert result["stitched_oos"]["n"] >= 100


def test_wf_gate_in_effectiveness(monkeypatch, wf_fixture_state):
  monkeypatch.setenv("EW_DIRECTION_GATES", "0")
  monkeypatch.setenv("EW_REGIME_GATES", "0")
  import engine.outcome_tracker as ot

  ot.TRACKED_PATH = wf_fixture_state
  from engine.walk_forward_validator import run_fee_walk_forward
  from engine.effectiveness_validation import evaluate_gates

  wf = run_fee_walk_forward(timeframe="1h", apply_policy=False)
  gates = evaluate_gates(
    pytest_result={"ok": True, "passed": 1, "failed": 0},
    metrics={"overall": {"win_rate": 0.75, "decided": 120}, "by_timeframe": {"1h": {"win_rate": 0.75, "n": 120}}},
    paper={"skipped": True},
    fitness={"fitness": 0.5},
    impact={"discovery": {"baseline_wr": 0.75}},
    reconciliation={},
    tracked_backtest={"ok": True, "win_rate": 0.75, "decided": 120, "expectancy_r": 0.1},
    wf_fee=wf,
  )
  wf_gate = next(g for g in gates if g.name == "wf_1h_fee_expectancy")
  assert wf_gate.passed is True
