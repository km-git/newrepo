"""Swarm-style composite fitness from tracked outcomes."""

from __future__ import annotations

from engine.strategy_fitness import (
  composite_fitness,
  profit_factor,
  sharpe_ratio,
  sortino_ratio,
  _r_returns_from_closed,
)


def test_composite_fitness_high_score():
  fit = composite_fitness(
    win_rate=0.62,
    return_pct=15.0,
    sharpe=1.5,
    sortino=2.0,
    profit_factor=2.0,
  )
  assert 0.5 < fit["fitness"] <= 1.0
  assert fit["weights"]["sharpe"] == 0.35


def test_sharpe_and_sortino():
  rets = [0.1, -0.05, 0.08, 0.02, -0.03, 0.12]
  assert sharpe_ratio(rets) is not None
  assert sortino_ratio(rets) is not None
  assert profit_factor(rets) is not None


def test_r_returns_from_closed():
  closed = [
    {"status": "sl_hit", "wae": 100.0, "stop_loss": 95.0, "tp1": 110.0},
    {"status": "tp1_hit", "wae": 100.0, "stop_loss": 95.0, "tp1": 110.0},
  ]
  rets = _r_returns_from_closed(closed)
  assert len(rets) == 2
  assert rets[0] == -1.0
  assert rets[1] > 0
