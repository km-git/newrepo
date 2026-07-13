"""Tests for market data gateway routing."""

from __future__ import annotations

import pandas as pd

from cache.disk_cache import CompressedCache
from cache.semantic_cache import SemanticOHLCVCache
from gateway.market_gateway import MarketDataGateway


def _fake_fetch(symbol, timeframes, limit, chain):
  idx = pd.date_range("2025-01-01", periods=limit, freq="1h", tz="UTC")
  df = pd.DataFrame(
    {"Open": 1.0, "High": 2.0, "Low": 0.5, "Close": 1.5, "Volume": 100.0},
    index=idx,
  )
  return {tf: df for tf in timeframes}


def test_bybit_first_chain():
  chain = MarketDataGateway.chain_for_preference("bybit")
  assert chain[0] == "bybit"
  assert "binance" in chain


def test_binance_first_chain():
  chain = MarketDataGateway.chain_for_preference("binance")
  assert chain[0] == "binance"
  assert "bybit" in chain


def test_gateway_semantic_cache_on_second_call(tmp_path, monkeypatch):
  from cache import disk_cache

  monkeypatch.setattr(disk_cache, "_global_cache", None)
  disk = CompressedCache(cache_dir=tmp_path, ttl=3600)
  cache = SemanticOHLCVCache(disk=disk)
  gw = MarketDataGateway(semantic_cache=cache, fetch_fn=_fake_fetch)
  r1 = gw.fetch_ohlcv("XRP/USDT", ["1h"], limit=100, exchange_preference="bybit")
  assert r1.cache_hits["1h"] == "miss"
  assert len(r1.data["1h"]) == 100

  r2 = gw.fetch_ohlcv("XRP/USDT", ["1h"], limit=80, exchange_preference="bybit")
  assert r2.cache_hits["1h"] in ("exact", "semantic")
  assert len(r2.data["1h"]) == 80
  assert cache.stats.semantic_hits + cache.stats.exact_hits >= 1


def test_repomix_pack_minifies():
  from gateway.repomix_export import pack_repository

  packed = pack_repository(".", includes=["cache/semantic_cache.py"], minify=True)
  assert "<repomix>" in packed
  assert "semantic_cache.py" in packed
  assert "class SemanticOHLCVCache" in packed
