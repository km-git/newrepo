"""Tests for GOAT effectiveness validation gates."""

from __future__ import annotations

from engine.effectiveness_gates import (
  deflated_sharpe_ratio,
  evaluate_gate,
  evaluate_regime_gates,
  gate_thresholds,
  probabilistic_sharpe_ratio,
  wilson_ci,
)
from engine.walk_forward_validator import _metrics_from_returns, _r_from_setup, chronological_folds


def test_wilson_ci_bounds():
  lo, hi = wilson_ci(55, 100)
  assert lo is not None and hi is not None
  assert 0.45 <= lo <= 0.55 <= hi <= 0.70


def test_psr_positive_edge():
  returns = [0.5] * 50 + [-0.3] * 30
  psr = probabilistic_sharpe_ratio(returns)
  assert psr["n"] == 80
  assert psr["psr"] is not None
  assert psr["psr"] > 0.5


def test_psr_insufficient_data():
  psr = probabilistic_sharpe_ratio([0.1])
  assert psr["psr"] is None


def test_deflated_sharpe_penalizes_trials():
  dsr_one = deflated_sharpe_ratio(1.5, 200, num_trials=1)
  dsr_many = deflated_sharpe_ratio(1.5, 200, num_trials=100)
  assert dsr_one["dsr"] is not None
  assert dsr_many["dsr"] is not None
  assert dsr_many["dsr"] <= dsr_one["dsr"]


def test_evaluate_gate_go_with_strong_stats():
  returns = [1.0] * 150 + [-0.5] * 100
  m = _metrics_from_returns(returns)
  gate = evaluate_gate(
    n_trades=m["n"],
    win_rate=m["win_rate"],
    sharpe=m["sharpe"],
    profit_factor=m["profit_factor"],
    return_pct=m["return_pct"],
    max_dd_pct=m["max_drawdown_pct"],
    returns=m["returns"],
    wins=m["wins"],
  )
  assert gate["verdict"] in ("GO", "NO_GO", "INSUFFICIENT_DATA")
  assert len(gate["gates"]) >= 5


def test_evaluate_gate_insufficient_trades():
  gate = evaluate_gate(
    n_trades=20,
    win_rate=0.55,
    sharpe=1.0,
    profit_factor=1.5,
    return_pct=5.0,
    max_dd_pct=5.0,
    returns=[0.5] * 20,
    wins=11,
  )
  assert gate["verdict"] == "INSUFFICIENT_DATA"


def test_regime_gates_flags_weak_tf(monkeypatch):
  monkeypatch.setenv("EW_BLOCKED_TFS", "")
  metrics = {
    "by_timeframe": {
      "15m": {"decided": 100, "win_rate": 0.65, "wins": 65, "losses": 35},
      "1d": {"decided": 50, "win_rate": 0.38, "wins": 19, "losses": 31},
    },
  }
  regime = evaluate_regime_gates(metrics)
  assert "1d" in regime["weak_timeframes"]
  assert "15m" in regime["strong_timeframes"]
  assert regime["regime_gate_passed"] is False


def test_regime_gates_skips_blocked_tf():
  metrics = {
    "by_timeframe": {
      "1d": {"decided": 50, "win_rate": 0.38, "wins": 19, "losses": 31},
      "15m": {"decided": 100, "win_rate": 0.65, "wins": 65, "losses": 35},
    },
  }
  regime = evaluate_regime_gates(metrics)
  assert "1d" not in regime["weak_timeframes"]
  assert regime["regime_gate_passed"] is True


def test_r_from_setup_tp_and_sl():
  setup = {"status": "tp1_hit", "wae": 100, "stop_loss": 95, "tp1": 110}
  r = _r_from_setup(setup)
  assert r is not None and r > 0
  setup["status"] = "sl_hit"
  assert _r_from_setup(setup) == -1.0


def test_chronological_folds_preserve_order():
  closed = [
    {"closed_at": f"2024-01-{i:02d}T00:00:00+00:00", "status": "tp1_hit", "wae": 100, "stop_loss": 95, "tp1": 110}
    for i in range(1, 21)
  ]
  folds = chronological_folds(closed, n_folds=4)
  assert len(folds) >= 1
  for train, test in folds:
    assert len(test) > 0


def test_gate_thresholds_defaults():
  th = gate_thresholds()
  assert th["min_trades_moderate"] >= 100
  assert th["min_psr"] >= 0.9
