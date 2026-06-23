"""Tests for calibrated execution layer."""

from __future__ import annotations

from engine.calibrated_execution import (
  apply_msb_pass_demotion,
  calibrated_size_pct,
  token_confidence_multiplier,
)


def test_msb_pass_demotion_full_to_monitor():
  setup = {
    "entry_signal": True,
    "execution_tier": "full",
    "status": "executable",
    "honest_reason": "SMC FULL",
    "indicator_signals": ["MSB z-score weak"],
  }
  msb = {"status": "ok", "pass": False, "tag": "MSB z-score weak", "z": 0.2}
  out = apply_msb_pass_demotion(setup, msb)
  assert out["status"] == "monitor"
  assert out["execution_tier"] == "none"
  assert out["msb_gate"] == "demoted_weak"


def test_anti_predictive_token_reduces_multiplier():
  mult = token_confidence_multiplier(["MSB z-score pass"], calibration={"available": False})
  assert mult < 1.0


def test_smc_cohort_sizing():
  setup = {"style": "smc", "execution_tier": "full", "indicators": {"active_tokens": []}}
  size, notes = calibrated_size_pct(setup, 100)
  assert size == 50.0
  assert any("smc_cohort" in n for n in notes)
