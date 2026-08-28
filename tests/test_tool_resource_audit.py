"""Tests for self-challenge tool/resource audit and new web intel sources."""

from __future__ import annotations

from engine.tool_resource_audit import run_tool_resource_audit
from core.tv_indicators import keltner_break, fisher_transform, compute_exploration_signals
import pandas as pd
import numpy as np


def _sample_df(n: int = 80) -> pd.DataFrame:
  rng = np.random.default_rng(7)
  close = 100 * np.cumprod(1 + rng.normal(0.001, 0.012, n))
  return pd.DataFrame({
    "Open": close,
    "High": close * 1.01,
    "Low": close * 0.99,
    "Close": close,
    "Volume": rng.uniform(1e3, 1e4, n),
  })


def test_keltner_break_and_fisher_implemented():
  df = _sample_df()
  kb = keltner_break(df)
  fi = fisher_transform(df)
  assert kb.get("available") is True
  assert fi.get("available") is True
  exp = compute_exploration_signals(df)
  assert exp["keltner_break"].get("available") is True
  assert exp["fisher"].get("available") is True


def test_tool_resource_audit_runs(tmp_path, monkeypatch):
  monkeypatch.setenv("EW_TOOL_AUDIT_STATE", str(tmp_path / "audit.json"))
  result = run_tool_resource_audit(persist=True)
  assert result.get("summary", {}).get("data_total", 0) >= 10
  assert "tv_oss" in result
  assert "known_gaps" in result
  assert result["summary"]["data_wired"] >= 10


def test_build_web_intel_extended(monkeypatch):
  monkeypatch.setattr(
    "gateway.web_intel.fear_greed_index",
    lambda: {"available": True, "value": 50, "label": "Neutral"},
  )
  monkeypatch.setattr(
    "gateway.web_intel.coingecko_global",
    lambda: {"available": True, "btc_dominance": 52.0},
  )
  monkeypatch.setattr(
    "gateway.web_intel.defillama_stablecoins",
    lambda: {"available": True, "total_stablecoin_mcap_usd": 100e9, "count": 40},
  )
  monkeypatch.setattr(
    "gateway.web_intel.defillama_total_tvl",
    lambda: {"available": True, "total_tvl_usd": 80e9, "tvl_change_pct": 0.5},
  )
  monkeypatch.setattr(
    "gateway.web_intel.macro_tradfi_snapshot",
    lambda: {"available": False},
  )
  monkeypatch.setattr(
    "gateway.web_intel.coingecko_coin_stats",
    lambda s: {"available": True, "symbol": "BTC", "change_24h_pct": 1.0, "momentum": "neutral"},
  )
  monkeypatch.setattr(
    "gateway.web_intel.funding_cross_check",
    lambda s: {"available": True, "avg_funding_rate_pct": 0.01, "consensus_bias": "neutral"},
  )
  monkeypatch.setattr(
    "gateway.web_intel.binance_open_interest",
    lambda s: {"available": True, "open_interest": 1e6, "oi_change_24h_pct": 2.0},
  )
  monkeypatch.setattr(
    "gateway.web_intel.oi_cross_check",
    lambda s: {"available": True, "total_oi": 2e6, "count": 2},
  )
  monkeypatch.setattr(
    "gateway.web_intel.binance_long_short_ratio",
    lambda s: {"available": True, "long_short_ratio": 1.1, "bias": "neutral"},
  )
  monkeypatch.setattr(
    "gateway.web_intel.binance_taker_ratio",
    lambda s: {"available": True, "buy_sell_ratio": 1.02, "bias": "neutral"},
  )
  monkeypatch.setattr(
    "gateway.web_intel.spot_perp_basis",
    lambda s: {"available": True, "basis_pct": 0.02, "bias": "neutral"},
  )
  monkeypatch.setattr(
    "gateway.web_intel.binance_recent_liquidations",
    lambda s: {"available": True, "count": 5, "bias": "balanced"},
  )
  monkeypatch.setattr("gateway.web_intel.binance_funding_public", lambda s: {"available": False})
  monkeypatch.setattr("gateway.web_intel.okx_funding_public", lambda s: {"available": False})
  monkeypatch.setattr("gateway.web_intel.bybit_funding_public", lambda s: {"available": False})

  from gateway.web_intel import build_web_intel

  intel = build_web_intel("BTC/USDT")
  assert "long_short_ratio" in intel
  assert "liquidations" in intel
  assert "defi_tvl" in intel
  assert len(intel["signals"]) >= 5
