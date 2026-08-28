"""Tests for OKX open interest in web intel."""

from __future__ import annotations

from gateway.web_intel import okx_open_interest, build_web_intel


def test_okx_open_interest_structure(monkeypatch):
  def fake_fetch(url, **kwargs):
    return {"data": [{"oi": "12345.6", "oiCcy": "12345.6"}]}

  monkeypatch.setattr("gateway.web_intel._fetch_json", fake_fetch)
  oi = okx_open_interest("BTC/USDT")
  assert oi.get("available") is True
  assert oi.get("open_interest") == 12345.6


def test_build_web_intel_includes_oi(monkeypatch):
  monkeypatch.setattr("gateway.web_intel.fear_greed_index", lambda: {"available": True, "value": 50, "label": "Neutral"})
  monkeypatch.setattr("gateway.web_intel.coingecko_global", lambda: {"available": True, "btc_dominance": 50})
  monkeypatch.setattr("gateway.web_intel.binance_funding_public", lambda s: {"available": False})
  monkeypatch.setattr("gateway.web_intel.okx_funding_public", lambda s: {"available": True, "funding_rate": 0.0001})
  monkeypatch.setattr("gateway.web_intel.okx_open_interest", lambda s: {"available": True, "open_interest": 99999})
  intel = build_web_intel("BTC/USDT")
  assert "open_interest" in intel
  assert intel["open_interest"].get("available") is True
