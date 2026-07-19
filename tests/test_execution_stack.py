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


def test_gate_allows_executable():
  ok, _ = gate_row(_row())
  assert ok is True


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
  from engine.execution_agent import execute_rows
  row = _row()
  result = execute_rows([row], dry_run=True)
  assert result["ok"] is True
  assert result["orders_submitted"] >= 1


def test_web_intel_fear_greed(monkeypatch):
  from gateway import web_intel

  def fake_fetch(url, **kwargs):
    return {"data": [{"value": "25", "value_classification": "Extreme Fear"}]}

  monkeypatch.setattr(web_intel, "_fetch_json", fake_fetch)
  fg = web_intel.fear_greed_index()
  assert fg["available"] is True
  assert fg["value"] == 25
