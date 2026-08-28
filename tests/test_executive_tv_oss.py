"""Tests for TV OSS executive integration and expanded web intel."""

from __future__ import annotations

import pandas as pd
import pytest

from engine.executive import executive_decide
from engine.executive_tv_oss import (
  apply_tv_oss_to_decision,
  build_tv_executive_context,
  tv_oss_executive_enabled,
)
from gateway.web_intel import build_web_intel, funding_cross_check


def _mock_data(close: float = 64000.0, n: int = 80) -> dict:
  idx = pd.date_range("2025-01-01", periods=n, freq="1h")
  trend = [close * (1 + 0.001 * i) for i in range(n)]
  base = pd.DataFrame(
    {
      "Open": trend,
      "High": [p * 1.005 for p in trend],
      "Low": [p * 0.995 for p in trend],
      "Close": trend,
      "Volume": [1e6] * n,
    },
    index=idx,
  )
  return {"1d": base, "1h": base, "15m": base}


def _base_decision(verdict: str = "CONDITIONAL_GO") -> dict:
  return {
    "status": "conditional_execute",
    "trade_setup": {
      "action": "conditional_long",
      "confidence": 0.55,
      "reason": "test setup",
      "entry_zone": [63000, 64000],
      "stop_loss": 62000,
      "take_profit_1": 66000,
      "take_profit_2": 68000,
      "risk_reward": 2.0,
    },
    "executive_decision": {
      "verdict": verdict,
      "conviction": "medium",
      "direction": "BULL",
      "position_size_pct": 50,
      "playbook": "probe",
      "structural_gaps": [],
    },
  }


def test_tv_oss_executive_enabled_default():
  assert tv_oss_executive_enabled() is True


def test_build_tv_executive_context_scores():
  data = _mock_data()
  ctx = build_tv_executive_context("BULL", data, {})
  assert ctx.get("enabled") is True
  assert 0 <= ctx["composite_score"] <= 100
  assert "tv_score" in ctx
  assert isinstance(ctx.get("signals"), list)


def test_apply_tv_oss_upgrades_on_strong_alignment():
  decision = _base_decision("CONDITIONAL_GO")
  tv_ctx = {
    "enabled": True,
    "composite_score": 75,
    "tv_score": 72,
    "aligned": True,
    "opposes": False,
    "signals": ["supertrend bullish"],
    "active_indicators": ["supertrend", "adx"],
  }
  out = apply_tv_oss_to_decision(decision, tv_ctx)
  assert out["executive_decision"]["verdict"] == "GO"
  assert out["executive_decision"]["position_size_pct"] > 50
  assert "tv_oss" in out["executive_decision"]


def test_apply_tv_oss_downgrades_on_opposition():
  decision = _base_decision("GO")
  decision["status"] = "execute"
  decision["executive_decision"]["verdict"] = "GO"
  decision["executive_decision"]["position_size_pct"] = 100
  tv_ctx = {
    "enabled": True,
    "composite_score": 32,
    "tv_score": 30,
    "aligned": False,
    "opposes": True,
    "signals": ["supertrend opposes"],
    "active_indicators": [],
  }
  out = apply_tv_oss_to_decision(decision, tv_ctx)
  assert out["executive_decision"]["verdict"] == "CONDITIONAL_GO"
  assert out["executive_decision"]["position_size_pct"] < 100


def test_executive_decide_with_market_tools_tv_oss():
  data = _mock_data(close=172000)
  market_tools = {"tv_confluence": {"score": 72, "aligned": True, "signals": ["trend aligned"]}}
  result = executive_decide(
    symbol="BTC/USDT",
    data=data,
    htf_class={"state": "correction_ABC", "bias": "bullish_reversal"},
    kz_low=171000,
    kz_high=173000,
    prior_fibs={},
    harmonic_overlaps=[],
    in_zone=True,
    execution_passes=True,
    exec_direction="BULL",
    bull_count=2,
    bear_count=0,
    violations_sample=[],
    mc_result={"empirical_probability": 0.6},
    market_tools=market_tools,
  )
  assert result["executive_decision"].get("tv_oss") is not None
  assert result["executive_decision"]["tv_oss"]["composite_score"] >= 0


def test_build_web_intel_structure(monkeypatch):
  monkeypatch.setattr(
    "gateway.web_intel.fear_greed_index",
    lambda: {"available": True, "value": 45, "label": "Neutral", "bias": "neutral"},
  )
  monkeypatch.setattr(
    "gateway.web_intel.coingecko_global",
    lambda: {"available": True, "btc_dominance": 52.0, "market_cap_change_24h_pct": 1.2},
  )
  monkeypatch.setattr(
    "gateway.web_intel.defillama_stablecoins",
    lambda: {"available": True, "total_stablecoin_mcap_usd": 150e9, "count": 50},
  )
  monkeypatch.setattr(
    "gateway.web_intel.coingecko_coin_stats",
    lambda s: {"available": True, "symbol": "BTC", "change_24h_pct": 2.1, "momentum": "bullish"},
  )
  monkeypatch.setattr(
    "gateway.web_intel.funding_cross_check",
    lambda s: {"available": True, "avg_funding_rate_pct": 0.01, "consensus_bias": "neutral", "count": 3},
  )
  monkeypatch.setattr(
    "gateway.web_intel.binance_open_interest",
    lambda s: {"available": True, "open_interest": 1e6, "oi_change_24h_pct": 3.5},
  )
  monkeypatch.setattr("gateway.web_intel.binance_funding_public", lambda s: {"available": False})
  monkeypatch.setattr("gateway.web_intel.okx_funding_public", lambda s: {"available": False})
  monkeypatch.setattr("gateway.web_intel.bybit_funding_public", lambda s: {"available": False})
  monkeypatch.setattr("gateway.web_intel.defillama_total_tvl", lambda: {"available": False})
  monkeypatch.setattr("gateway.web_intel.macro_tradfi_snapshot", lambda: {"available": False})
  monkeypatch.setattr("gateway.web_intel.oi_cross_check", lambda s: {"available": False})
  monkeypatch.setattr("gateway.web_intel.binance_long_short_ratio", lambda s: {"available": False})
  monkeypatch.setattr("gateway.web_intel.binance_taker_ratio", lambda s: {"available": False})
  monkeypatch.setattr("gateway.web_intel.spot_perp_basis", lambda s: {"available": False})
  monkeypatch.setattr("gateway.web_intel.binance_recent_liquidations", lambda s: {"available": False})

  intel = build_web_intel("BTC/USDT")
  assert intel["fear_greed"]["available"] is True
  assert intel["stablecoins"]["available"] is True
  assert intel["funding_cross"]["available"] is True
  assert intel["open_interest"]["available"] is True
  assert len(intel["signals"]) >= 3


def test_funding_cross_check_aggregation(monkeypatch):
  monkeypatch.setattr(
    "gateway.web_intel.binance_funding_public",
    lambda s: {"available": True, "funding_rate": 0.0002},
  )
  monkeypatch.setattr(
    "gateway.web_intel.okx_funding_public",
    lambda s: {"available": True, "funding_rate": 0.00015},
  )
  monkeypatch.setattr(
    "gateway.web_intel.bybit_funding_public",
    lambda s: {"available": True, "funding_rate": 0.00018},
  )
  result = funding_cross_check("BTC/USDT")
  assert result["available"] is True
  assert result["consensus_bias"] == "long_crowded"
  assert result["count"] == 3
