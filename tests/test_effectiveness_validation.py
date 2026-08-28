"""Tests for effectiveness validation harness."""

from __future__ import annotations

import json

import pytest


@pytest.fixture(autouse=True)
def _isolated_effectiveness_paths(tmp_path, monkeypatch):
  monkeypatch.setenv("EW_PORTFOLIO_STATE", str(tmp_path / "portfolio_state.json"))
  monkeypatch.setenv("EW_EFFECTIVENESS_JSON", str(tmp_path / "eff.json"))
  monkeypatch.setenv("EW_EFFECTIVENESS_MD", str(tmp_path / "EFF.md"))


def test_evaluate_gates_pass_fixture():
  from engine.effectiveness_validation import evaluate_gates

  gates = evaluate_gates(
    pytest_result={"ok": True, "passed": 50, "failed": 0},
    metrics={
      "overall": {"win_rate": 0.61, "decided": 500, "wins": 305, "losses": 195},
      "by_timeframe": {"1h": {"win_rate": 0.86, "n": 100}},
    },
    paper={
      "ok": True,
      "realized_pnl_usd": -500,
      "simulated": 5,
      "wins": 2,
      "losses": 3,
      "starting_equity_usd": 50000,
      "ending_equity_usd": 49500,
      "candidates": 20,
    },
    fitness={"fitness": 0.52, "n_trades": 100, "sharpe": 0.8},
    impact={"ok": True, "discovery": {"baseline_wr": 0.55}, "balanced_weights": {"weights": {"1h": 1.0}}},
    reconciliation={
      "outcome_tracker_win_rate": 0.61,
      "paper_win_rate": 0.40,
      "delta": 0.21,
      "note": "test",
    },
    tracked_backtest={
      "ok": True,
      "win_rate": 0.58,
      "decided": 200,
      "realized_pnl_usd": 1200,
      "equity_start": 50000,
      "equity_end": 51200,
      "fees_usd": 400,
      "wins": 116,
      "losses": 84,
    },
  )
  names = {g.name: g.passed for g in gates}
  assert names["pytest_subset"] is True
  assert names["outcome_win_rate"] is True
  assert names["timeframe_1h_win_rate"] is True
  assert names["strategy_fitness"] is True
  assert names["tracked_fee_backtest"] is True
  assert names["live_paper_sim"] is True  # profit not required by default


def test_evaluate_gates_fail_low_win_rate():
  from engine.effectiveness_validation import evaluate_gates

  gates = evaluate_gates(
    pytest_result={"ok": True, "passed": 10, "failed": 0},
    metrics={"overall": {"win_rate": 0.42, "decided": 200, "wins": 84, "losses": 116}, "by_timeframe": {}},
    paper={"ok": True, "simulated": 0, "realized_pnl_usd": 0},
    fitness={"composite": 0.3},
    impact={"ok": True, "baseline_wr": 0.42},
    reconciliation={},
  )
  wr_gate = next(g for g in gates if g.name == "outcome_win_rate")
  assert wr_gate.passed is False


def test_reconcile_models():
  from engine.effectiveness_validation import reconcile_models

  recon = reconcile_models(
    {"overall": {"win_rate": 0.61, "decided": 1000}},
    {"wins": 1, "losses": 2, "simulated": 3},
  )
  assert recon["outcome_tracker_win_rate"] == 0.61
  assert recon["paper_win_rate"] == pytest.approx(0.333, abs=0.01)
  assert recon["delta"] is not None


def test_tracked_fee_backtest_on_state():
  from engine.effectiveness_validation import run_tracked_fee_backtest

  result = run_tracked_fee_backtest(equity=50_000)
  assert result.get("ok") is True
  assert result.get("decided", 0) >= 100
  assert result.get("win_rate") is not None


def test_summarize_metrics_dimensions():
  from engine.effectiveness_validation import summarize_metrics_dimensions

  dims = summarize_metrics_dimensions({
    "by_timeframe": {"1h": {"wins": 10, "losses": 2, "n": 12, "win_rate": 0.83}},
    "by_direction": {"LONG": {"wins": 5, "losses": 1, "n": 6, "win_rate": 0.83}},
  })
  assert dims["by_timeframe"][0]["timeframe"] == "1h"
  assert dims["by_direction"][0]["direction"] == "LONG"


def test_write_effectiveness_reports(tmp_path, monkeypatch):
  monkeypatch.setenv("EW_EFFECTIVENESS_JSON", str(tmp_path / "eff.json"))
  monkeypatch.setenv("EW_EFFECTIVENESS_MD", str(tmp_path / "EFF.md"))
  from engine.effectiveness_validation import EffectivenessReport, GateResult, write_effectiveness_reports

  report = EffectivenessReport(
    ok=False,
    generated_at="2026-08-28T00:00:00+00:00",
    gates=[GateResult("test_gate", False, value=0.4, threshold=0.55, detail="low")],
    sections={"metrics": {"overall": {"win_rate": 0.4}}},
    summary="0/1 gates passed",
  )
  jpath, mpath = write_effectiveness_reports(report)
  assert (tmp_path / "eff.json").exists()
  assert (tmp_path / "EFF.md").exists()
  data = json.loads((tmp_path / "eff.json").read_text())
  assert data["ok"] is False
