"""Tests for batch/parallel OHLC prefetch."""

from __future__ import annotations

from engine.ohlc_fetch import group_pairs_by_symbol, prefetch_ohlc, prefetch_stats


def test_group_pairs_by_symbol_dedupes_timeframes():
  pairs = [
    ("BTC/USDT", "1h"),
    ("BTC/USDT", "4h"),
    ("ETH/USDT", "1h"),
    ("BTC/USDT", "1h"),
  ]
  grouped = group_pairs_by_symbol(pairs)
  assert grouped["BTC/USDT"] == ["4h", "1h"]
  assert grouped["ETH/USDT"] == ["1h"]


def test_prefetch_ohlc_batches_by_symbol():
  calls = []

  def fake_fetch(sym, tfs, is_crypto=True):
    calls.append((sym, tuple(tfs), is_crypto))
    return {tf: f"df-{sym}-{tf}" for tf in tfs}

  pairs = [
    ("BTC/USDT", "1h"),
    ("BTC/USDT", "4h"),
    ("ETH/USDT", "1h"),
  ]
  cache = prefetch_ohlc(pairs, is_crypto=True, fetch_fn=fake_fetch)
  assert len(calls) == 2
  assert ("BTC/USDT", ("4h", "1h"), True) in calls
  assert cache["BTC/USDT|1h"] == "df-BTC/USDT-1h"
  assert cache["ETH/USDT|1h"] == "df-ETH/USDT-1h"


def test_prefetch_stats():
  stats = prefetch_stats([("A/USDT", "1h"), ("A/USDT", "4h"), ("B/USDT", "1h")])
  assert stats["unique_pairs"] == 3
  assert stats["symbols"] == 2
  assert stats["fetch_calls"] == 2
