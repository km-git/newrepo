"""Tests for incremental outcome resolution."""

from __future__ import annotations

import json
from datetime import datetime, timedelta, timezone

import pytest

from engine.outcome_tracker import _setup_needs_resolve, resolve_open_setups


def _iso(hours_ago: float = 0) -> str:
  return (datetime.now(timezone.utc) - timedelta(hours=hours_ago)).isoformat()


def test_setup_needs_resolve_incremental_skips_recent_check(monkeypatch):
  monkeypatch.setenv("EW_RESOLVE_RECHECK_HOURS", "6")
  now = datetime.now(timezone.utc).timestamp()
  setup = {
    "symbol": "BTC/USDT",
    "timeframe": "1h",
    "recorded_at": _iso(48),
    "last_checked_at": _iso(1),
  }
  assert _setup_needs_resolve(setup, now_ts=now, mode="incremental") is False
  assert _setup_needs_resolve(setup, now_ts=now, mode="full") is True


def test_setup_needs_resolve_respects_min_age(monkeypatch):
  monkeypatch.setenv("EW_RESOLVE_MIN_AGE_HOURS", "2")
  now = datetime.now(timezone.utc).timestamp()
  setup = {
    "symbol": "BTC/USDT",
    "timeframe": "1h",
    "recorded_at": _iso(0.5),
  }
  assert _setup_needs_resolve(setup, now_ts=now, mode="full") is False


def test_resolve_uses_prefetch(monkeypatch, tmp_path):
  monkeypatch.setattr("engine.outcome_tracker.TRACKED_PATH", tmp_path / "tracked.json")
  recorded = _iso(24)
  tmp_path.joinpath("tracked.json").write_text(
    json.dumps({
      "open": [{
        "id": "BTC/USDT|1h|LONG",
        "symbol": "BTC/USDT",
        "timeframe": "1h",
        "direction": "LONG",
        "wae": 100,
        "stop_loss": 95,
        "tp1": 110,
        "recorded_at": recorded,
        "status": "open",
      }],
      "closed": [],
    }),
    encoding="utf-8",
  )

  import pandas as pd

  idx = pd.date_range("2026-01-01", periods=5, freq="h", tz="UTC")
  df = pd.DataFrame({
    "High": [101.0, 102.0, 103.0, 104.0, 111.0],
    "Low": [99.0, 100.0, 101.0, 102.0, 103.0],
    "Close": [100.0, 101.0, 102.0, 103.0, 110.0],
  }, index=idx)

  calls = []

  def fake_prefetch(pairs, is_crypto=True):
    calls.append(list(pairs))
    return {f"{sym}|{tf}": df for sym, tf in pairs}

  monkeypatch.setattr("engine.ohlc_fetch.prefetch_ohlc", fake_prefetch)
  monkeypatch.setenv("EW_RESOLVE_MODE", "full")
  monkeypatch.setenv("EW_PAPER_FORWARD_SKIP_RESOLVE", "0")

  assert resolve_open_setups(is_crypto=True, resolve_mode="full") == 1
  assert calls == [[("BTC/USDT", "1h")]]
  state = json.loads(tmp_path.joinpath("tracked.json").read_text())
  assert state["open"] == []
  assert state["closed"][0]["status"] == "tp1_hit"
