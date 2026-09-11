"""Tests for impact discovery and balanced signal weights."""

from __future__ import annotations

import json

from engine.impact_discovery import (
  build_balanced_weights,
  discover_impact_factors,
  match_setup_factors,
  rank_data_sources,
)


def _closed_state():
  closed = []
  for i in range(20):
    closed.append({
      "status": "tp1_hit" if i < 14 else "sl_hit",
      "timeframe": "4h",
      "direction": "SHORT",
      "gtc_tier": "executable",
      "honest_execution_tier": "probe",
      "wave_structure": "bear_impulse_5",
      "consensus": "BEAR",
    })
  for i in range(10):
    closed.append({
      "status": "sl_hit" if i < 7 else "tp1_hit",
      "timeframe": "1w",
      "direction": "LONG",
      "gtc_tier": "executable",
      "honest_execution_tier": "probe",
      "wave_structure": "invalid_impulse",
      "consensus": "BULL",
    })
  return {"open": [], "closed": closed}


def test_discover_finds_tf_lift():
  d = discover_impact_factors(_closed_state())
  assert d["sample_size"] == 30
  assert d["baseline_wr"] is not None
  boosts = {f["factor"]: f for f in d["top_boosts"]}
  assert "tf:4h" in boosts or any("4h" in f for f in boosts)


def test_balanced_weights_capped():
  d = discover_impact_factors(_closed_state())
  bal = build_balanced_weights(d, max_active=5)
  assert bal["active_count"] <= 5
  for v in bal["weights"].values():
    assert -0.12 <= v <= 0.12


def test_match_setup_factors():
  keys = match_setup_factors(timeframe="4h", direction="SHORT", honest_tier="probe")
  assert "tf:4h" in keys
  assert "dir:SHORT" in keys


def test_rank_data_sources():
  d = discover_impact_factors(_closed_state())
  ranked = rank_data_sources(d)
  assert len(ranked) >= 5
  assert ranked[0].get("priority") in ("high", "medium", "low")
