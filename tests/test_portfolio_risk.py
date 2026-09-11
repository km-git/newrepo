"""Tests for portfolio heat, hedging, and dynamic risk overlays."""

from __future__ import annotations

import os

import pytest


@pytest.fixture(autouse=True)
def _isolated_portfolio_state(monkeypatch, tmp_path):
  monkeypatch.setenv("EW_PORTFOLIO_STATE", str(tmp_path / "portfolio_state.json"))


def _row(symbol="SOL/USDT", direction="LONG", risk_pct=1.0, risk_budget=100.0, equity=10000.0):
  return {
    "symbol": symbol,
    "direction": direction,
    "account_risk_pct": risk_pct,
    "gtc_size_cap_pct": 100,
    "gtc_tier": "executable",
    "honest_status": "executable",
    "account_equity": equity,
    "risk_budget_usd": risk_budget,
    "timeframe": "1h",
  }


def test_correlation_shrink():
  from engine.portfolio_risk import correlation_shrink

  assert correlation_shrink(0) == 1.0
  assert correlation_shrink(0.75) < 1.0
  assert correlation_shrink(1.0) == pytest.approx(0.707, abs=0.01)


def test_symbol_cluster():
  from engine.portfolio_risk import symbol_cluster

  assert symbol_cluster("BTC/USDT") == "btc"
  assert symbol_cluster("ETH/USDT") == "eth"
  assert symbol_cluster("SOL/USDT") == "high_beta"
  assert symbol_cluster("RANDOM/USDT") == "alt"


def test_portfolio_heat_blocks_at_cap(monkeypatch):
  monkeypatch.setenv("EW_PORTFOLIO_RISK", "1")
  monkeypatch.setenv("EW_PORTFOLIO_HEAT_PCT", "6")
  from engine.portfolio_risk import PortfolioState, gate_portfolio_heat, portfolio_heat_multiplier

  state = PortfolioState(equity=10000, total_heat_pct=5.5)
  row = _row(risk_pct=1.0, risk_budget=100)
  mult, factors = portfolio_heat_multiplier(state, row)
  assert mult == 0.0
  allowed, reasons = gate_portfolio_heat(row, state)
  assert allowed is False
  assert any("portfolio heat" in r for r in reasons)


def test_portfolio_heat_elevated_shrinks(monkeypatch):
  monkeypatch.setenv("EW_PORTFOLIO_RISK", "1")
  monkeypatch.setenv("EW_PORTFOLIO_HEAT_PCT", "6")
  from engine.portfolio_risk import PortfolioState, portfolio_heat_multiplier

  state = PortfolioState(equity=10000, total_heat_pct=4.0)
  row = _row(risk_pct=0.5, risk_budget=50)
  mult, factors = portfolio_heat_multiplier(state, row)
  assert mult <= 0.75
  assert factors


def test_recommend_hedge_on_divergence(monkeypatch):
  monkeypatch.setenv("EW_HEDGE_RECOMMEND", "1")
  from engine.portfolio_risk import recommend_hedge

  hedge = recommend_hedge(
    symbol="BTC/USDT",
    direction="BULL",
    consensus={"agreement_pct": 50, "divergences": ["ewa: BEAR"]},
    in_zone=True,
    execution_passes=False,
  )
  assert hedge["enabled"] is True
  assert hedge["recommended_size_pct"] <= 50
  ids = {s["id"] for s in hedge["strategies"]}
  assert "partial_probe" in ids
  assert "contingent_dual" in ids


def test_recommend_btc_perp_hedge_for_high_beta(monkeypatch):
  monkeypatch.setenv("EW_HEDGE_RECOMMEND", "1")
  from engine.portfolio_risk import recommend_hedge

  hedge = recommend_hedge(
    symbol="SOL/USDT",
    direction="LONG",
    consensus={"agreement_pct": 45, "divergences": ["internal: BEAR"]},
    btc_correlation=0.82,
    in_zone=True,
    execution_passes=False,
  )
  ids = {s["id"] for s in hedge["strategies"]}
  assert "btc_perp_hedge" in ids
  perp = next(s for s in hedge["strategies"] if s["id"] == "btc_perp_hedge")
  assert perp["hedge_ratio"] >= 0.7


def test_apply_hedge_to_executive():
  from engine.portfolio_risk import apply_hedge_to_executive

  ex = {"verdict": "CONDITIONAL_GO", "position_size_pct": 100, "contingencies": []}
  hedge = {
    "enabled": True,
    "recommended_size_pct": 50,
    "strategies": [{
      "id": "partial_probe",
      "action": "reduce",
      "trigger": "immediate",
      "rationale": "test",
    }],
  }
  out = apply_hedge_to_executive(ex, hedge)
  assert out["position_size_pct"] == 50
  assert out.get("hedge_plan") == hedge
  assert len(out["contingencies"]) == 1


def test_apply_portfolio_risk_to_row_shrinks_cap(monkeypatch):
  monkeypatch.setenv("EW_PORTFOLIO_RISK", "1")
  monkeypatch.setenv("EW_PORTFOLIO_HEAT_PCT", "6")
  from engine.portfolio_risk import PortfolioState, apply_portfolio_risk_to_row

  state = PortfolioState(equity=10000, total_heat_pct=4.5, cluster_heat={"high_beta": 1.5})
  row = _row(symbol="SOL/USDT", risk_pct=0.5, risk_budget=50)
  out = apply_portfolio_risk_to_row(row, state)
  assert float(out.get("gtc_size_cap_pct", 100)) < 100
  assert out.get("portfolio_heat_mult") is not None


def test_apply_portfolio_risk_update_state_accumulates(monkeypatch):
  monkeypatch.setenv("EW_PORTFOLIO_RISK", "1")
  monkeypatch.setenv("EW_PORTFOLIO_HEAT_PCT", "6")
  from engine.portfolio_risk import PortfolioState, apply_portfolio_risk_to_row

  state = PortfolioState(equity=10000)
  row = _row(symbol="BTC/USDT", risk_pct=1.0, risk_budget=100)
  out = apply_portfolio_risk_to_row(row, state, update_state=True)
  assert out.get("gtc_size_cap_pct", 100) == 100
  assert state.total_heat_pct > 0
  assert state.open_count == 1
  assert len(state.positions) == 1
  assert state.positions[0]["symbol"] == "BTC/USDT"


def test_execution_gate_blocks_heat(monkeypatch):
  monkeypatch.setenv("EW_PORTFOLIO_RISK", "1")
  monkeypatch.setenv("EW_PORTFOLIO_HEAT_PCT", "6")
  from engine.execution_gates import gate_row
  from engine.portfolio_risk import PortfolioState, save_portfolio_state

  save_portfolio_state(PortfolioState(equity=10000, total_heat_pct=5.8))
  row = {
    "gtc_tier": "executable",
    "symbol": "BTC/USDT",
    "direction": "LONG",
    "account_risk_pct": 1.0,
    "gtc_size_cap_pct": 100,
    "risk_budget_usd": 100,
    "account_equity": 10000,
    "executive_verdict": "GO",
  }
  allowed, reasons = gate_row(row)
  assert allowed is False
