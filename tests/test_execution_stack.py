"""Tests for execution router, gates, proxy pool, web intel."""

from __future__ import annotations

import pytest

from engine.execution_gates import gate_row
from engine.execution_router import filter_executable_rows, row_to_orders
from gateway.antibot import browser_headers, random_user_agent
from gateway.proxy_pool import ProxyPool


def _row(**kwargs):
  base = {
    "symbol": "BTC/USDT",
    "timeframe": "15m",
    "direction": "LONG",
    "row_type": "primary",
    "gtc_tier": "executable",
    "honest_execution_tier": "probe",
    "gtc_size_cap_pct": 50,
    "executive_verdict": "CONDITIONAL_GO",
    "executive_action": "EXECUTE_CAUTION",
    "macro_mode": "NEUTRAL",
    "stop_loss": 95000,
    "tp1": 105000,
    "tp1_exit_pct": 40,
    "position_notional_usd": 1000,
    "dca_legs": [
      {"leg": 1, "price": 100000, "size_pct": 10},
      {"leg": 2, "price": 99000, "size_pct": 20},
    ],
    "leg1_usd": 100,
    "leg2_usd": 200,
  }
  base.update(kwargs)
  return base


def test_row_to_orders_produces_legs():
  orders = row_to_orders(_row())
  limits = [o for o in orders if o["type"] == "limit"]
  assert len(limits) == 2
  assert limits[0]["side"] == "buy"
  assert limits[0]["client_id"].startswith("ew-")


def test_row_to_orders_derives_sizing_from_risk_fields():
  import json
  legs = [{"leg": 1, "price": 100000, "size_pct": 10}, {"leg": 2, "price": 99000, "size_pct": 20}]
  orders = row_to_orders(_row(
    dca_legs=json.dumps(legs),
    position_notional_usd=0,
    leg1_usd=0,
    leg2_usd=0,
    account_risk_pct=0.75,
    wae=99500,
    stop_loss=95000,
    account_equity=10000,
  ))
  limits = [o for o in orders if o["type"] == "limit"]
  assert len(limits) == 2
  assert limits[0]["notional_usd"] > 0


def test_gate_blocks_nuke():
  ok, reasons = gate_row(_row(macro_mode="NUKE"))
  assert ok is False
  assert "macro_nuke" in reasons[0]


def test_gate_allows_executable(monkeypatch):
  monkeypatch.setenv("EW_DIRECTION_GATES", "0")
  ok, _ = gate_row(_row())
  assert ok is True


def test_gate_blocks_weak_regime_tf(monkeypatch):
  monkeypatch.setenv("EW_REGIME_GATES", "1")
  metrics = {
    "by_timeframe": {
      "1d": {"decided": 50, "win_rate": 0.38, "wins": 19, "losses": 31},
    },
  }
  monkeypatch.setattr("engine.outcome_tracker.load_metrics", lambda: metrics)
  ok, reasons = gate_row(_row(timeframe="1d"))
  assert ok is False
  assert any("regime_weak" in r or "tf_blocked" in r for r in reasons)


def test_gate_blocks_1d_by_default(monkeypatch):
  monkeypatch.setenv("EW_REGIME_GATES", "0")
  ok, reasons = gate_row(_row(timeframe="1d"))
  assert ok is False
  assert any("tf_blocked" in r for r in reasons)


def test_gate_blocks_weak_long_direction(monkeypatch):
  monkeypatch.setenv("EW_DIRECTION_GATES", "1")
  metrics = {
    "by_direction": {
      "LONG": {"decided": 50, "win_rate": 0.42, "wins": 21, "losses": 29},
      "SHORT": {"decided": 50, "win_rate": 0.62, "wins": 31, "losses": 19},
    },
  }
  monkeypatch.setattr("engine.outcome_tracker.load_metrics", lambda: metrics)
  ok, reasons = gate_row(_row(direction="LONG"))
  assert ok is False
  assert any("direction_blocked_LONG" in r for r in reasons)
  ok_short, _ = gate_row(_row(direction="SHORT"))
  assert ok_short is True


def test_filter_closed_applies_regime_weak_tf(monkeypatch):
  from engine.execution_gates import filter_closed_for_policy

  monkeypatch.setenv("EW_BLOCKED_TFS", "")
  monkeypatch.setenv("EW_DIRECTION_GATES", "0")
  metrics = {
    "by_timeframe": {
      "4h": {"decided": 40, "win_rate": 0.35, "wins": 14, "losses": 26},
    },
    "by_direction": {},
  }
  closed = [
    {"timeframe": "4h", "direction": "SHORT", "status": "tp1_hit"},
    {"timeframe": "15m", "direction": "SHORT", "status": "tp1_hit"},
  ]
  out = filter_closed_for_policy(closed, metrics)
  assert len(out) == 1
  assert out[0]["timeframe"] == "15m"


def test_filter_executable_rows():
  rows = [_row(), _row(gtc_tier="monitor"), _row(macro_mode="NUKE")]
  out = filter_executable_rows(rows)
  assert len(out) == 1


def test_proxy_pool_rotation():
  pool = ProxyPool(["http://a:1", "http://b:2"])
  assert pool.next() == "http://a:1"
  assert pool.next() == "http://b:2"


def test_browser_headers():
  h = browser_headers()
  assert "User-Agent" in h
  assert len(random_user_agent()) > 10


def test_execution_agent_dry_run(monkeypatch):
  monkeypatch.setenv("EW_WEB_INTEL", "0")
  monkeypatch.setenv("EW_WS_ENABLED", "0")
  monkeypatch.setenv("EW_EXECUTION_CONSENSUS_LLM", "0")
  monkeypatch.setenv("EW_LLM_EW_BYPASS", "1")
  monkeypatch.setenv("EW_DIRECTION_GATES", "0")
  monkeypatch.delenv("CURSOR_API_KEY", raising=False)
  from engine.execution_agent import execute_rows
  row = _row(consensus="BULL", agreement_pct=85, engines_valid=3)
  result = execute_rows([row], dry_run=True)
  assert result["ok"] is True
  assert result["orders_submitted"] >= 1


def test_execution_agent_batch_portfolio_heat(monkeypatch, tmp_path):
  monkeypatch.setenv("EW_WEB_INTEL", "0")
  monkeypatch.setenv("EW_WS_ENABLED", "0")
  monkeypatch.setenv("EW_EXECUTION_CONSENSUS", "0")
  monkeypatch.setenv("EW_PORTFOLIO_RISK", "1")
  monkeypatch.setenv("EW_PORTFOLIO_HEAT_PCT", "6")
  monkeypatch.setenv("EW_PORTFOLIO_STATE", str(tmp_path / "portfolio_state.json"))
  from engine.execution_agent import execute_rows

  row = _row(
    consensus="BULL",
    agreement_pct=85,
    engines_valid=3,
    account_risk_pct=2.9,
    risk_budget_usd=290,
    account_equity=10000,
  )
  result = execute_rows(
    [row, dict(row, symbol="ETH/USDT"), dict(row, symbol="SOL/USDT")],
    dry_run=True,
  )
  assert result["ok"] is True
  assert result["orders_submitted"] >= 1
  assert len(result["blocked"]) >= 1
  assert any("portfolio heat" in " ".join(b.get("reasons", [])).lower() for b in result["blocked"])


def test_web_intel_fear_greed(monkeypatch):
  from gateway import web_intel

  def fake_fetch(url, **kwargs):
    return {"data": [{"value": "25", "value_classification": "Extreme Fear"}]}

  monkeypatch.setattr(web_intel, "_fetch_json", fake_fetch)
  fg = web_intel.fear_greed_index()
  assert fg["available"] is True
  assert fg["value"] == 25
