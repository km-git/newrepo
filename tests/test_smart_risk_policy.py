"""Tests for always-on smart risk policy."""

from __future__ import annotations

from engine.execution_advanced import ExportContext, select_dca_profile
from engine.smart_risk_policy import (
  always_smart_enabled,
  apply_account_risk_pct,
  default_dca_profile,
  dca_splits_label,
  stamp_row_policy,
  validate_row_policy,
)


def test_always_smart_default_on():
  assert always_smart_enabled() is True
  assert default_dca_profile() == "pyramid_4"


def test_select_dca_pyramid_default():
  ctx = ExportContext()
  result = {"symbol": "SOL/USDT", "step9_market_confluence": {}}
  profile, reason = select_dca_profile("SOL/USDT", "1h", result, ctx)
  assert profile == "pyramid_4"
  assert "10/20/30/40" in reason


def test_select_dca_30_70_on_high_correlation():
  ctx = ExportContext()
  result = {
    "symbol": "ADA/USDT",
    "step9_market_confluence": {"btc_correlation": {"correlation": 0.82, "high_beta": True}},
  }
  profile, reason = select_dca_profile("ADA/USDT", "1d", result, ctx)
  assert profile == "two_layer_30_70"
  assert "correlation" in reason.lower()


def test_select_dca_static_pyramid_when_smart_off(monkeypatch):
  monkeypatch.setenv("EW_ALWAYS_SMART_RISK", "0")
  ctx = ExportContext()
  result = {
    "symbol": "ADA/USDT",
    "step9_market_confluence": {"btc_correlation": {"correlation": 0.82}},
  }
  profile, _ = select_dca_profile("ADA/USDT", "1d", result, ctx)
  assert profile == "pyramid_4"


def test_stamp_preserves_30_70_profile():
  row = stamp_row_policy({
    "symbol": "ADA/USDT",
    "timeframe": "1d",
    "direction": "SHORT",
    "dca_profile": "two_layer_30_70",
    "stop_loss": 1.0,
    "tp1": 1.1,
    "stop_architecture": "smart_dynamic_sl",
  })
  assert row["dca_splits_pct"] == "30,70"
  ok, issues = validate_row_policy(row)
  assert ok is True
  assert issues == []


def test_stamp_and_validate_pyramid_row():
  row = stamp_row_policy({
    "symbol": "BTC/USDT",
    "timeframe": "1h",
    "direction": "SHORT",
    "stop_loss": 90000,
    "tp1": 88000,
    "tp1_exit_pct": 50,
    "tp2_exit_pct": 25,
    "tp3_exit_pct": 25,
    "dca_profile": "pyramid_4",
    "stop_architecture": "smart_dynamic_sl",
  })
  assert row["dca_splits_pct"] == "10,20,30,40"
  ok, issues = validate_row_policy(row)
  assert ok is True
  assert row["smart_risk_policy"] == "always_smart_risk_v1"


def test_apply_dynamic_risk_enabled(monkeypatch):
  monkeypatch.setenv("EW_ALWAYS_SMART_RISK", "1")
  out = apply_account_risk_pct(0.75, {"mult": 0.8, "enabled": True, "factors": ["test"]})
  assert out == 0.6


def test_dca_splits_label():
  assert dca_splits_label("pyramid_4") == "10,20,30,40"
  assert dca_splits_label("two_layer_30_70") == "30,70"
