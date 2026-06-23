"""Tests for calibrated execution layer."""

from __future__ import annotations

from engine.calibrated_execution import (
  apply_msb_pass_demotion,
  calibrated_size_pct,
  token_confidence_multiplier,
)


def test_msb_pass_demotion_blocks_executable():
  setup = {
    "entry_signal": True,
    "entry_probe": True,
    "execution_tier": "full",
    "status": "executable",
    "honest_reason": "SMC FULL",
    "indicator_signals": ["MSB z-score pass"],
  }
  msb = {"status": "ok", "pass": True, "tag": "MSB z-score pass", "z": 2.0}
  out = apply_msb_pass_demotion(setup, msb)
  assert out["entry_signal"] is False
  assert out["entry_probe"] is False
  assert out["status"] == "monitor"
  assert out["msb_gate"] == "blocked_pass"


def test_anti_predictive_token_reduces_multiplier():
  mult = token_confidence_multiplier(["MSB z-score pass"], calibration={"available": False})
  assert mult < 1.0


def test_smc_cohort_sizing():
  setup = {"style": "smc", "execution_tier": "full", "indicators": {"active_tokens": []}}
  size, notes = calibrated_size_pct(setup, 100)
  assert size == 50.0
  assert any("smc_cohort" in n for n in notes)
