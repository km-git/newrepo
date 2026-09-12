"""Tests for accurate setup scoring."""

from __future__ import annotations

from engine.accurate_setups import extract_accurate_setups, score_setup_accuracy


def _setup(**kwargs):
  base = {
    "status": "monitor",
    "execution_tier": "none",
    "direction": "LONG",
    "readiness_score": 60,
    "wave_valid": False,
    "oos_win_rate": 0.62,
    "oos_trades": 10,
    "autodream_verdict": "validated",
    "stop_loss": {"price": 95, "distance_pct": 3.0},
    "entry": {"anchor": 100, "order_type": "limit"},
    "targets": [{"price": 105, "rr": 1.0}, {"price": 110, "rr": 2.0}],
    "honest_reason": "monitor",
  }
  base.update(kwargs)
  return base


def test_score_executable_passed_oos_gate():
  s = _setup(
    status="executable",
    execution_tier="full",
    oos_gate="passed",
    wave_valid=True,
    oos_win_rate=0.68,
  )
  score, tier, tags = score_setup_accuracy(s, "day_trade")
  assert tier == "A"
  assert score >= 70
  assert "executable" in tags


def test_broken_stop_geometry_excluded():
  s = _setup(stop_loss={"price": 500, "distance_pct": 50.0})
  score, tier, tags = score_setup_accuracy(s, "scalp")
  assert tier == "X"
  assert score == 0


def test_extract_accurate_setups_filters():
  results = [{
    "symbol": "BTC/USDT",
    "status": "active",
    "executive_decision": {"verdict": "GO"},
    "step6_wave_consensus": {"consensus_direction": "BULL"},
    "step8_outcomes": {
      "setups": {
        "swing": _setup(oos_win_rate=0.70, wave_valid=True),
        "scalp": _setup(oos_win_rate=0.30, autodream_verdict="caution"),
      },
    },
  }]
  rows = extract_accurate_setups(results, min_tier="C")
  assert len(rows) == 1
  assert rows[0]["symbol"] == "BTC/USDT"
