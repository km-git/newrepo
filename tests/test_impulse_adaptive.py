"""Tests for adaptive impulse and research setup export."""

from __future__ import annotations

from core.impulse import ADAPTIVE_R1_MAX_RATIO, validate_impulse
from engine.accurate_setups import extract_research_setups
from engine.indicator_calibration import build_hybrid_weights
from tests.test_validation import _synthetic_impulse


def test_adaptive_r1_allows_deep_retrace():
  ratio = 1.08
  mws = _synthetic_impulse(w2_ratio=ratio)
  strict = validate_impulse(mws, mode="strict")
  adaptive = validate_impulse(mws, mode="adaptive")
  assert not strict["passes"]
  assert adaptive["passes"]
  assert ratio < ADAPTIVE_R1_MAX_RATIO


def test_hybrid_weights_restore_neutral_signals():
  cal = {
    "available": True,
    "signal_weights": {"in kill zone": 28},
    "blocked_signals": ["RSI weakness intact"],
    "style_thresholds": {"swing": 58},
  }
  hybrid, blocked, thresholds = build_hybrid_weights(cal)
  assert "in kill zone" in hybrid
  assert "near zone" in hybrid
  assert "RSI weakness intact" not in hybrid
  assert "RSI weakness intact" in blocked
  assert thresholds["swing"] <= 58


def test_research_export_all_styles():
  setup = {
    "status": "monitor",
    "execution_tier": "none",
    "direction": "LONG",
    "readiness_score": 60,
    "wave_valid": False,
    "oos_win_rate": 0.62,
    "oos_trades": 8,
    "autodream_verdict": "validated",
    "stop_loss": {"price": 95, "distance_pct": 3},
    "entry": {"anchor": 100, "order_type": "limit", "zone": [99, 101]},
    "targets": [{"price": 105, "rr": 1}, {"price": 110, "rr": 2}],
    "honest_reason": "monitor",
    "timeframe": "1d",
    "horizon": "2d-4w",
  }
  results = [{
    "symbol": "BTC/USDT",
    "status": "active",
    "executive_decision": {"verdict": "GO"},
    "step6_wave_consensus": {"consensus_direction": "BULL"},
    "step8_outcomes": {"setups": {"swing": setup, "scalp": {**setup, "status": "not_actionable"}}},
  }]
  rows = extract_research_setups(results)
  assert len(rows) == 2
  assert {r["timeframe"] for r in rows if r["style"] == "swing"} == {"1d"}
