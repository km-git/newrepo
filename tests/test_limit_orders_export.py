"""Tests for pair×TF limit order export (250 rows, honest tier gates)."""

from __future__ import annotations

import json
from pathlib import Path

import pytest

from core.risk import DCA_SPLITS
from engine.limit_orders_export import (
  ALL_TIMEFRAMES,
  build_all_limit_orders,
  build_limit_order_row,
  export_limit_orders,
)


def _sample_result(symbol: str = "BTC/USDT") -> dict:
  return {
    "symbol": symbol,
    "status": "staged_entry",
    "step1_htf_bias": {"wave_C_current": 100.0},
    "step2_adaptive_pivots": {"1h": {"atr_14": 2.0}, "15m": {"atr_14": 1.0}},
    "step2_wave_structure": {
      "1h": {"structure": "impulse_up", "current_price": 100.0, "impulse_valid": True},
      "4h": {"structure": "impulse_up", "current_price": 100.0, "impulse_partial": True},
      "15m": {"structure": "abc", "current_price": 100.0},
    },
    "step3_kill_zone": {
      "price_low": 98.0,
      "price_high": 102.0,
      "constituent_fibs": {"fib_0.618": 99.0, "fib_0.786": 98.5},
    },
    "step3_c_targets": {"c_target_100": 110.0, "c_target_161": 115.0},
    "step4_harmonic_overlap": [{"tf": "4h", "prz_low": 97.5, "prz_high": 99.5}],
    "step5_execution_validation": {"in_zone": True},
    "step6_wave_consensus": {"consensus_direction": "BULL", "agreement_pct": 70},
    "executive_decision": {"verdict": "STAGED_GO", "direction": "BULL"},
    "step8_outcomes": {
      "honest_summary": {"primary_direction": "LONG"},
      "setups": {
        "scalp": {
          "status": "executable",
          "execution_tier": "probe",
          "direction": "LONG",
          "timeframe": "15m",
          "entry": {"anchor": 100.0, "zone": [99.0, 101.0], "order_type": "limit"},
          "stop_loss": {"price": 95.0, "rule": "structure"},
          "targets": [
            {"price": 105.0, "exit_pct": 40, "rr": 1.5},
            {"price": 110.0, "exit_pct": 30, "rr": 2.0},
            {"price": 115.0, "exit_pct": 30, "rr": 3.0},
          ],
          "readiness_score": 0.8,
          "indicator_signals": ["rsi_oversold"],
        },
        "day_trade": {
          "status": "monitor",
          "execution_tier": "none",
          "direction": "LONG",
          "timeframe": "1h",
          "entry": {"anchor": 100.0, "zone": [98.0, 102.0], "order_type": "limit"},
          "stop_loss": {"price": 94.0},
          "targets": [
            {"price": 108.0, "exit_pct": 40, "rr": 1.5},
            {"price": 112.0, "exit_pct": 30, "rr": 2.0},
            {"price": 116.0, "exit_pct": 30, "rr": 2.5},
          ],
        },
        "swing": {"status": "not_actionable", "direction": "LONG", "timeframe": "1d", "entry": {"anchor": 100.0}},
        "long_term": {
          "status": "monitor",
          "direction": "LONG",
          "timeframe": "1w",
          "entry": {"anchor": 100.0, "zone": [95.0, 105.0]},
          "stop_loss": {"price": 90.0},
          "targets": [
            {"price": 120.0, "exit_pct": 40, "rr": 2.0},
            {"price": 125.0, "exit_pct": 30, "rr": 2.5},
            {"price": 130.0, "exit_pct": 30, "rr": 3.0},
          ],
        },
      },
    },
  }


def test_dca_splits():
  assert DCA_SPLITS == [10, 20, 30, 40]


def test_build_limit_order_row_executable_and_monitor_tiers():
  result = _sample_result()
  scalp = build_limit_order_row(result, "15m")
  day = build_limit_order_row(result, "1h")
  ctx4h = build_limit_order_row(result, "4h")

  assert scalp["gtc_tier"] == "executable"
  assert scalp["honest_execution_tier"] == "probe"
  assert day["gtc_tier"] == "monitor"
  assert ctx4h["gtc_tier"] in ("monitor", "watch")
  assert scalp["order_type"] == "limit"
  assert scalp["time_in_force"] == "GTC"
  assert scalp["entry_zone_low"] == pytest.approx(99.0)
  assert scalp["entry_zone_high"] == pytest.approx(101.0)


def test_build_limit_order_row_has_dca_legs():
  row = build_limit_order_row(_sample_result(), "1h")
  assert len(row["dca_legs"]) == 4
  assert [leg["size_pct"] for leg in row["dca_legs"]] == DCA_SPLITS
  assert all(leg["order_type"] == "limit" for leg in row["dca_legs"])
  assert all(leg["time_in_force"] == "GTC" for leg in row["dca_legs"])
  assert row.get("wae")
  assert row.get("dca_architecture") == "asymmetric_pyramid_10_20_30_40"


def test_build_all_limit_orders_row_count():
  results = [_sample_result("A/USDT"), _sample_result("B/USDT")]
  rows = build_all_limit_orders(results)
  assert len(rows) == 2 * len(ALL_TIMEFRAMES)


def test_export_limit_orders_writes_csv(tmp_path: Path):
  results = [_sample_result("A/USDT"), _sample_result("B/USDT")]
  meta = export_limit_orders(results, output_dir=tmp_path, write_json=True)
  assert meta["row_count"] == 2 * len(ALL_TIMEFRAMES)
  assert meta["expected_rows"] == 250
  assert Path(meta["csv"]).exists()
  assert Path(meta["latest_csv"]).exists()
  assert Path(meta["json"]).exists()
  assert sum(meta["tier_counts"].values()) == meta["row_count"]


@pytest.mark.skipif(
  not list(Path("output").glob("top50_analysis_*.json")),
  reason="no batch output on disk",
)
def test_export_real_batch_250_rows(tmp_path: Path):
  latest = sorted(
    Path("output").glob("top50_analysis_*.json"),
    key=lambda p: p.stat().st_mtime,
    reverse=True,
  )[0]
  results = json.loads(latest.read_text(encoding="utf-8"))
  meta = export_limit_orders(results, output_dir=tmp_path)
  assert meta["row_count"] == len(results) * len(ALL_TIMEFRAMES)
  if len(results) == 50:
    assert meta["row_count"] == 250
