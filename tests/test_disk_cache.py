"""Tests for sqlite+msgpack CompressedCache (no pickle / no diskcache)."""

from __future__ import annotations

import pickle

import pandas as pd

from cache.disk_cache import CompressedCache, _dumps, _loads


def test_roundtrip_dataframe_dict(tmp_path):
  idx = pd.date_range("2025-01-01", periods=8, freq="1h", tz="UTC")
  df = pd.DataFrame(
    {"Open": 1.0, "High": 2.0, "Low": 0.5, "Close": 1.5, "Volume": 100.0},
    index=idx,
  )
  cache = CompressedCache(cache_dir=tmp_path, ttl=3600)
  cache.set("ohlcv", {"1h": df}, "BTC/USDT", "1h")
  out = cache.get("ohlcv", "BTC/USDT", "1h")
  assert out is not None
  assert list(out["1h"].columns) == ["Open", "High", "Low", "Close", "Volume"]
  assert len(out["1h"]) == 8
  assert float(out["1h"]["Close"].iloc[-1]) == 1.5


def test_blobs_are_not_pickle(tmp_path):
  cache = CompressedCache(cache_dir=tmp_path, ttl=3600)
  cache.set("ns", {"ok": True, "n": 3}, "k")
  blobs = list((tmp_path / "blobs").glob("*.zst"))
  assert blobs
  raw = blobs[0].read_bytes()
  assert pickle.dumps({"ok": True, "n": 3}) not in raw
  assert b"diskcache" not in raw


def test_msgpack_codec_rejects_nothing_jsonlike():
  payload = {"a": 1, "b": [1, 2, 3], "c": "x"}
  assert _loads(_dumps(payload)) == payload


def test_get_or_compute_and_invalidate(tmp_path):
  cache = CompressedCache(cache_dir=tmp_path, ttl=3600)
  calls = {"n": 0}

  def compute():
    calls["n"] += 1
    return {"v": calls["n"]}

  v1, hit1 = cache.get_or_compute("ns", compute, "x")
  v2, hit2 = cache.get_or_compute("ns", compute, "x")
  assert hit1 is False
  assert hit2 is True
  assert v1 == v2 == {"v": 1}
  assert cache.invalidate_namespace("ns") == 1
  assert cache.get("ns", "x") is None
