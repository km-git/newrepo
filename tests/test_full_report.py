"""Tests for unified full analysis export."""

from __future__ import annotations

from engine.full_report import build_full_row, build_setup_rows


def _sample_result():
  return {
    "symbol": "BTC/USDT",
    "status": "staged_entry",
    "step1_htf_bias": {
      "state": "choppy",
      "bias": "neutral",
      "wave_A": {"type": "Down", "start": 100, "end": 80},
      "wave_B_end": 90,
      "wave_C_current": 85,
    },
    "step3_kill_zone": {"price_low": 82, "price_high": 88, "cluster_meta": {}},
    "step3_c_targets": {"c_target_100": 70, "c_target_161": 60},
    "step4_harmonic_scan": {},
    "step4_harmonic_overlap": [],
    "step5_execution_validation": {"in_zone": False, "passes": False, "violations_sample": []},
    "step6_wave_consensus": {"consensus_direction": "BEAR", "agreement_pct": 75},
    "step2_wave_structure": {
      "1d": {"structure": "abc_correction", "direction": "BEAR", "impulse_valid": False, "wave_sizes": {}},
    },
    "trade_setup": {
      "action": "scale_short",
      "entry_zone": [82, 88],
      "stop_loss": 92,
      "take_profit_1": 80,
      "take_profit_2": 75,
      "risk_reward": 1.5,
      "confidence": 0.5,
    },
    "executive_decision": {
      "verdict": "STAGED_GO",
      "direction": "BEAR",
      "playbook": "scale",
      "conviction": 0.5,
      "position_size_pct": 50,
      "structural_gaps": ["no 15m impulse"],
    },
    "step8_outcomes": {
      "honest_summary": {
        "truth": "0 executable, 2 monitor, 2 skip",
        "primary_style": "scalp",
        "primary_status": "monitor",
        "executable_count": 0,
        "monitor_count": 2,
        "not_actionable_count": 2,
      },
      "setups": {
        "scalp": {
          "status": "monitor",
          "direction": "SHORT",
          "timeframe": "15m",
          "horizon": "15m-4h",
          "honest_reason": "await impulse",
          "wave_structure": "abc",
          "wave_valid": False,
          "entry": {"anchor": 85, "zone": [82, 88]},
          "dca": [{"price": 85, "size_pct": 10}],
          "stop_loss": {"price": 90},
          "targets": [{"price": 83}, {"price": 80, "rr": 2.0}],
          "risk": {"account_risk_pct": 0.5},
        },
      },
    },
  }


def test_full_row_includes_all_styles():
  row = build_full_row(_sample_result())
  assert row["symbol"] == "BTC/USDT"
  assert row["scalp_status"] == "monitor"
  assert row["outcome_truth"] == "0 executable, 2 monitor, 2 skip"
  assert row["1d_structure"] == "abc_correction"


def test_setup_rows_per_style():
  rows = build_setup_rows(_sample_result())
  assert len(rows) == 1  # only scalp in sample
  assert rows[0]["style"] == "scalp"
  assert rows[0]["htf_state"] == "choppy"
