"""Smart risk stack: pyramid DCA, dynamic SL, dynamic targets."""

from __future__ import annotations

import os

import pytest

from core.risk import DCA_PROFILE_PYRAMID, DCA_SPLITS
from engine.execution_advanced import ExportContext, build_contingent_scenarios, select_dca_profile
from engine.limit_orders_export import build_limit_order_row
from engine.smart_risk import SMART_STOP_ARCH, SMART_TARGET_ARCH, resolve_dca_profile
from tests.test_limit_orders_export import _sample_result


def test_default_dca_profile_is_pyramid():
  ctx = ExportContext()
  result = {
    "symbol": "SOL/USDT",
    "step9_market_confluence": {"btc_correlation": {"correlation": 0.35}},
  }
  profile, reason = select_dca_profile("SOL/USDT", "1h", result, ctx)
  assert profile == DCA_PROFILE_PYRAMID
  assert "10/20/30/40" in reason


def test_legacy_two_layer_opt_in(monkeypatch):
  monkeypatch.setenv("EW_ALLOW_ALT_DCA_PROFILES", "1")
  ctx = ExportContext()
  result = {
    "symbol": "ADA/USDT",
    "step9_market_confluence": {"btc_correlation": {"correlation": 0.82}},
  }
  profile, _ = resolve_dca_profile("ADA/USDT", "1d", result, ctx)
  assert profile == "two_layer_30_70"


def test_limit_order_row_smart_stack():
  row = build_limit_order_row(_sample_result(), "15m")
  assert row["dca_splits_pct"] == ",".join(str(x) for x in DCA_SPLITS)
  assert row["dca_architecture"] == "asymmetric_pyramid_10_20_30_40"
  assert row["stop_architecture"] == SMART_STOP_ARCH
  assert row["target_architecture"] == SMART_TARGET_ARCH
  assert len(row["dca_legs"]) == 4
  assert sum(leg["size_pct"] for leg in row["dca_legs"]) == 100


def test_contingent_scenarios_use_pyramid_dca():
  result = {
    "symbol": "BTC/USDT",
    "step3_kill_zone": {"price_low": 61000, "price_high": 62500},
    "step2_wave_structure": {
      "1h": {"current_price": 62000, "waves_last5": [{"start": 63000, "end": 61000}]},
    },
    "step2_adaptive_pivots": {"1h": {"atr_14": 500}},
    "step1_htf_bias": {"wave_C_current": 62000},
  }
  scenarios = build_contingent_scenarios(result, "1h", {"atr_mult_sl": 1.2, "max_stop_atr": 4.0}, ExportContext())
  for sc in scenarios:
    assert sc["dca_profile"] == DCA_PROFILE_PYRAMID
    assert len(sc["dca"]) == 4
    assert sc["stop"].get("architecture") == SMART_STOP_ARCH
    assert sc["targets"][0].get("architecture") == SMART_TARGET_ARCH
