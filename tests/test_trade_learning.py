"""Tests for failed-trade learning, risk tuning, and hedge plans."""

from __future__ import annotations

import pandas as pd

from engine.trade_learning import (
  analyze_failures,
  apply_learning_to_setup,
  build_hedge_plan,
  classify_loss,
  suggest_risk_adjustments,
)


def test_classify_loss_broad_stop():
  trade = {
    "symbol": "ETH/USDT",
    "style": "swing",
    "direction": "SHORT",
    "entry": 100.0,
    "stop": 250.0,
    "paper_outcome": "loss",
    "bars_held": 1,
    "exit_detail": "stop@1",
    "readiness_score": 55,
    "execution_tier": "probe",
    "honest_reason": "invalid_impulse",
  }
  c = classify_loss(trade)
  assert "stop_too_broad" in c["modes"]
  assert "structure_gap" in c["modes"]


def test_build_hedge_plan_when_sl_broad():
  setup = {
    "style": "swing",
    "direction": "SHORT",
    "entry": {"anchor": 100.0},
    "stop_loss": {"price": 300.0, "distance_pct": 200.0},
    "execution_tier": "probe",
    "honest_reason": "swing PROBE",
  }
  hedge = build_hedge_plan(setup, "SOL/USDT")
  assert hedge is not None
  assert hedge["required"] is True
  assert hedge["hedge_direction"] == "LONG"
  assert hedge["hedge_size_pct"] >= 25


def test_build_hedge_plan_skips_tight_sl():
  setup = {
    "style": "scalp",
    "direction": "LONG",
    "entry": {"anchor": 100.0},
    "stop_loss": {"price": 98.0, "distance_pct": 2.0},
  }
  assert build_hedge_plan(setup, "BTC/USDT") is None


def test_analyze_failures_from_ledger():
  ledger = [
    {"paper_outcome": "loss", "symbol": "A/USDT", "style": "scalp", "entry": 1, "stop": 2,
     "direction": "LONG", "bars_held": 1, "exit_detail": "stop@1", "readiness_score": 40,
     "execution_tier": "probe", "honest_reason": "invalid"},
    {"paper_outcome": "win", "symbol": "B/USDT", "style": "scalp"},
    {"paper_outcome": "loss", "symbol": "A/USDT", "style": "scalp", "entry": 1, "stop": 2,
     "direction": "LONG", "bars_held": 2, "exit_detail": "stop@2", "readiness_score": 45,
     "execution_tier": "probe", "honest_reason": "probe"},
  ]
  r = analyze_failures(ledger)
  assert r["available"] is True
  assert r["losses_analyzed"] == 2
  assert len(r["lessons"]) >= 1


def test_apply_learning_adds_hedge_and_lesson():
  learning = {
    "available": True,
    "lessons": ["Probe losses without impulse — cut probe size"],
    "by_symbol": {"ZEC/USDT": 3},
    "by_style": {"swing": {"losses": 5, "top_modes": {}}},
    "mode_counts": {"stop_too_broad": 4, "probe_unconfirmed": 3},
  }
  setup = {
    "style": "swing",
    "status": "executable",
    "execution_tier": "probe",
    "direction": "SHORT",
    "entry": {"anchor": 100.0, "zone": [95, 105]},
    "stop_loss": {"price": 400.0, "distance_pct": 300.0, "rule": "wide"},
    "risk": {"account_risk_pct": 1.0, "sizing_rule": "base"},
    "honest_reason": "swing PROBE",
  }
  out = apply_learning_to_setup(setup, "ZEC/USDT", None, learning)
  assert out.get("hedge_plan") is not None
  assert out.get("loss_lesson")
  assert out["risk"]["account_risk_pct"] < 1.0


def test_suggest_risk_adjustments_symbol_hotspot():
  learning = {
    "by_symbol": {"TEST/USDT": 4},
    "by_style": {},
    "mode_counts": {},
  }
  setup = {
    "style": "day_trade",
    "direction": "LONG",
    "entry": {"anchor": 50.0},
    "stop_loss": {"price": 48.0, "distance_pct": 4.0},
    "risk": {"account_risk_pct": 0.75},
  }
  adj = suggest_risk_adjustments(setup, None, learning, "TEST/USDT")
  assert adj["size_multiplier"] < 1.0
  assert any("symbol" in a for a in adj["adjustments"])
