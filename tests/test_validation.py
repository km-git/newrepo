"""Unit tests for R1/R2/R3, ABC, skip, kill zone, and schema validation."""

from __future__ import annotations

import json

import numpy as np
import pandas as pd
import pytest

from core.correction import detect_abc
from core.fib_zone import compute_tight_kill_zone
from core.impulse import validate_impulse
from core.monowaves import compute_skip
from schemas.models import ElliottWaveOutput


def _synthetic_impulse(w2_ratio: float = 0.5, w4_overlap: bool = False) -> list:
  """Build 5 monowaves: bullish impulse with configurable W2 retrace."""
  w1 = 100.0
  w2 = w1 * w2_ratio
  w3 = 150.0
  w4 = 40.0
  w5 = 80.0
  p0 = 1000.0
  p1 = p0 + w1
  p2 = p1 - w2
  p3 = p2 + w3
  p4 = p3 - w4 if not w4_overlap else p0 - 10  # overlap W1 end
  p5 = p4 + w5
  return [
    {"type": "Up", "price_start": p0, "price_end": p1},
    {"type": "Down", "price_start": p1, "price_end": p2},
    {"type": "Up", "price_start": p2, "price_end": p3},
    {"type": "Down", "price_start": p3, "price_end": p4},
    {"type": "Up", "price_start": p4, "price_end": p5},
  ]


def test_r1_fails_at_105_percent():
  mws = _synthetic_impulse(w2_ratio=1.05)
  val = validate_impulse(mws)
  assert not val["passes"]
  assert any("R1" in v for v in val["violations"])


def test_r1_passes_at_50_percent():
  mws = _synthetic_impulse(w2_ratio=0.5)
  val = validate_impulse(mws)
  assert val["passes"]
  assert val["direction"] == "BULL"


def test_r3_fails_on_w4_overlap():
  mws = _synthetic_impulse(w4_overlap=True)
  val = validate_impulse(mws)
  assert not val["passes"]
  assert "R3" in val["violations"]


def test_abc_passes_61_retrace():
  a_mag = 100.0
  mws = [
    {"type": "Down", "price_start": 1100, "price_end": 1000},
    {"type": "Up", "price_start": 1000, "price_end": 1061},
    {"type": "Down", "price_start": 1061, "price_end": 1040},
  ]
  abc = detect_abc(mws)
  assert abc is not None
  assert abc["wave_B"]["retrace_pct"] == pytest.approx(61.0, abs=1)


def test_abc_fails_105_retrace():
  mws = [
    {"type": "Down", "price_start": 1100, "price_end": 1000},
    {"type": "Up", "price_start": 1000, "price_end": 1105},
    {"type": "Down", "price_start": 1105, "price_end": 1050},
  ]
  assert detect_abc(mws) is None


def test_adaptive_skip():
  assert compute_skip(600, 200) == 30
  assert compute_skip(10, 200) == 3


def test_tight_kill_zone_cluster():
  low, high, meta = compute_tight_kill_zone(75000, 75519, {"fib_0.236": 74944}, 74000, max_width_pct=2.0)
  width_pct = (high - low) / 74000 * 100
  assert width_pct <= 5.0
  assert low < high
  assert meta.get("cluster") or meta.get("anchor")


def test_executive_schema_always_actionable():
  sample = {
    "symbol": "TEST",
    "timestamp_utc": "2026-01-01T00:00:00+00:00",
    "status": "staged_entry",
    "step1_htf_bias": {
      "tf": "1d",
      "state": "choppy",
      "wave_A": {"type": "Up", "magnitude": 1.0, "start": 1.0, "end": 2.0},
      "wave_B_end": 1.5,
      "wave_C_current": 1.6,
      "bias": "neutral",
    },
    "step2_adaptive_pivots": {"1d": {"skip": 3, "monowave_count": 5}},
    "step3_kill_zone": {"price_low": 1.0, "price_high": 2.0, "width_pct": 1.0},
    "step4_harmonic_overlap": [],
    "step5_execution_validation": {"in_zone": False, "passes": False},
    "step2_wave_structure": {"1d": {"tf": "1d", "structure": "abc_correction", "direction": "BULL", "impulse_valid": False, "violations": [], "wave_sizes": {}, "waves_last5": []}},
    "step3_c_targets": {"c_target_100": 100.0, "c_direction": "up"},
    "step4_harmonic_scan": {},
    "step6_wave_consensus": {
      "consensus_direction": "BULL",
      "consensus_score": 0.55,
      "agreement_pct": 60.0,
      "conviction": "medium",
      "confidence_boost": 0.02,
      "engines_run": 5,
      "engines_valid": 2,
      "votes": [{
        "engine": "internal_1d",
        "source": "internal",
        "direction": "BULL",
        "valid": True,
        "confidence": 0.8,
        "detail": "test",
      }],
      "divergences": [],
      "github_tools_used": ["github.com/drstevendev/ElliottWaveAnalyzer"],
    },
    "step8_outcomes": {
      "honest_summary": {"primary_style": "swing", "primary_status": "monitor", "truth": "test"},
      "setups": {},
      "autodream": {"by_style": {}, "history_entries": 0},
    },
    "trade_setup": {
      "action": "scale_long",
      "entry_zone": [1.4, 1.6],
      "stop_loss": 1.2,
      "take_profit_1": 2.0,
      "confidence": 0.45,
      "reason": "staged fib pathway",
    },
    "executive_decision": {
      "verdict": "STAGED_GO",
      "conviction": "moderate",
      "direction": "BULL",
      "position_size_pct": 100,
      "playbook": "Scale in across fib levels",
      "structural_gaps": ["no harmonic overlap"],
      "contingencies": [{"if": "TP1 hit", "then": "trail stop"}],
    },
    "honesty_audit": {"hard_cap_applied": True, "executive_mode": True},
    "tool_calls_log": [{"tool": "fetch", "args": "{}", "result_hash": "abc"}],
    "reasoning_trace": "executive staged entry",
  }
  out = ElliottWaveOutput(**sample)
  assert out.trade_setup.entry_zone is not None
  assert out.executive_decision.verdict == "STAGED_GO"
