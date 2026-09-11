"""Tests for semantic OHLCV cache."""

from __future__ import annotations

import time

import pandas as pd
import pytest

from cache.disk_cache import CompressedCache
from cache.semantic_cache import SemanticOHLCVCache, normalize_symbol, semantic_key

NAMESPACE = "semantic_ohlcv"


def _make_df(n: int = 100) -> pd.DataFrame:
  idx = pd.date_range("2025-01-01", periods=n, freq="1h", tz="UTC")
  return pd.DataFrame(
    {"Open": 1.0, "High": 2.0, "Low": 0.5, "Close": 1.5, "Volume": 100.0},
    index=idx,
  )


def test_normalize_symbol():
  assert normalize_symbol("btcusdt") == "BTC/USDT"
  assert normalize_symbol("BTC-USDT") == "BTC/USDT"
  assert normalize_symbol("ETH/USDT") == "ETH/USDT"


def test_semantic_key_stable():
  k1 = semantic_key("BTC/USDT", "1h", ("okx",))
  k2 = semantic_key("btc/usdt", "1h", ("okx",))
  assert k1 == k2


def test_semantic_hit_serves_subset(tmp_path):
  disk = CompressedCache(cache_dir=tmp_path, ttl=3600)
  cache = SemanticOHLCVCache(disk=disk)
  chain = ("okx",)
  df = _make_df(500)
  cache.put("BTC/USDT", "1h", 500, chain, "okx", df)

  out, hit = cache.get("BTC/USDT", "1h", 300, chain)
  assert hit == "semantic"
  assert out is not None
  assert len(out) == 300


def test_exact_hit(tmp_path):
  disk = CompressedCache(cache_dir=tmp_path, ttl=3600)
  cache = SemanticOHLCVCache(disk=disk)
  chain = ("okx",)
  df = _make_df(100)
  cache.put("ETH/USDT", "4h", 100, chain, "okx", df)

  out, hit = cache.get("ETH/USDT", "4h", 100, chain)
  assert hit == "exact"
  assert len(out) == 100


def test_miss_when_expired(tmp_path):
  disk = CompressedCache(cache_dir=tmp_path, ttl=3600)
  cache = SemanticOHLCVCache(disk=disk)
  chain = ("okx",)
  df = _make_df(50)
  cache.put("SOL/USDT", "15m", 50, chain, "okx", df)

  # Expire on disk (in-memory index alone is not authoritative)
  sem = semantic_key("SOL/USDT", "15m", chain)
  disk_key = cache._disk_key(sem, 50)
  blob = disk.get(NAMESPACE, disk_key)
  blob["fetched_at"] = time.time() - 120
  disk.set(NAMESPACE, blob, disk_key)
  cache._index.clear()

  out, hit = cache.get("SOL/USDT", "15m", 50, chain)
  assert hit == "miss"
  assert out is None
