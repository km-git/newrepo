"""Tests for advanced execution: profiles, macro, contingent, dollar sizing."""

from __future__ import annotations

from engine.execution_advanced import (
  ExportContext,
  MacroState,
  build_contingent_scenarios,
  compute_leg_dollars,
  expand_contingent_rows,
  select_dca_profile,
)
from core.risk import build_dca_ladder, compute_wae


def test_two_layer_10_90_profile():
  legs = build_dca_ladder("LONG", 100.0, 2.0, 95.0, 105.0, profile="two_layer_10_90")
  assert [l["size_pct"] for l in legs] == [10, 90]
  assert legs[0]["price"] >= legs[1]["price"]


def test_two_layer_30_70_profile():
  legs = build_dca_ladder("SHORT", 100.0, 2.0, 95.0, 105.0, profile="two_layer_30_70")
  assert [l["size_pct"] for l in legs] == [30, 70]
  assert legs[0]["price"] <= legs[1]["price"]


def test_macro_nuke_cancels_longs():
  ctx = ExportContext(macro=MacroState(usdt_d_pct=9.0))
  from engine.execution_advanced import apply_macro_to_row
  row = apply_macro_to_row({"symbol": "JTO/USDT", "direction": "LONG", "gtc_tier": "executable"}, ctx)
  assert row["macro_mode"] == "NUKE"
  assert row["gtc_tier"] == "watch"


def test_macro_long_upgrade_boost():
  ctx = ExportContext(macro=MacroState(usdt_d_pct=8.0))
  from engine.execution_advanced import apply_macro_to_row
  row = apply_macro_to_row(
    {"symbol": "JTO/USDT", "direction": "LONG", "gtc_tier": "executable", "account_risk_pct": 0.75},
    ctx,
  )
  assert row["macro_mode"] == "LONG_UPGRADE"
  assert row["account_risk_pct"] > 0.75


def test_dollar_sizing_from_equity():
  legs = build_dca_ladder("LONG", 100.0, 2.0, 95.0, 105.0)
  wae = compute_wae(legs)
  sizing = compute_leg_dollars(10000, legs, wae, 90.0, 0.75, 100)
  assert sizing["risk_budget_usd"] == 75.0
  assert sizing["position_notional_usd"] > 0
  assert sum(sizing["leg_usd"].values()) == sizing["position_notional_usd"]


def test_select_correlation_cap_profile():
  ctx = ExportContext()
  result = {
    "symbol": "ADA/USDT",
    "step9_market_confluence": {"btc_correlation": {"correlation": 0.82, "high_beta": True}},
  }
  profile, reason = select_dca_profile("ADA/USDT", "1d", result, ctx)
  assert profile == "two_layer_30_70"
  assert "correlation" in reason.lower()


def test_btc_contingent_scenarios():
  result = {
    "symbol": "BTC/USDT",
    "step3_kill_zone": {"price_low": 61000, "price_high": 62500},
    "step2_wave_structure": {
      "1h": {"current_price": 62000, "waves_last5": [{"start": 63000, "end": 61000}]},
    },
    "step2_adaptive_pivots": {"1h": {"atr_14": 500}},
    "step1_htf_bias": {"wave_C_current": 62000},
  }
  cfg = {"atr_mult_sl": 1.2, "max_stop_atr": 4.0}
  scenarios = build_contingent_scenarios(result, "1h", cfg, ExportContext())
  assert len(scenarios) == 2
  ids = {s["scenario_id"] for s in scenarios}
  assert ids == {"short_breakdown", "long_floor"}


def test_expand_contingent_child_rows():
  base = {"symbol": "BTC/USDT", "timeframe": "1h", "row_type": "primary", "gtc_tier": "monitor"}
  scenarios = build_contingent_scenarios(
    {
      "symbol": "BTC/USDT",
      "step3_kill_zone": {"price_low": 61000, "price_high": 62500},
      "step2_wave_structure": {"1h": {"current_price": 62000}},
      "step2_adaptive_pivots": {"1h": {"atr_14": 500}},
    },
    "1h",
    {"atr_mult_sl": 1.2, "max_stop_atr": 4.0},
    ExportContext(),
  )
  children = expand_contingent_rows(base, scenarios)
  assert len(children) == 2
  assert children[0]["row_type"] == "contingent_scenario"
