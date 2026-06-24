"""Tests for institutional edge Phases 1–5."""

from __future__ import annotations

import numpy as np
import pandas as pd

from core.institutional_edge import (
  build_institutional_matrix,
  compute_cvd,
  compute_volume_profile,
  detect_cvd_divergence,
  detect_entry_confirmation,
  run_smc_library,
  structure_blocks_entry,
)
from engine.institutional_setups import build_smc_setup


def _ohlcv(n: int = 150) -> pd.DataFrame:
  rng = np.random.default_rng(7)
  close = 100 + np.cumsum(rng.normal(0, 0.4, n))
  return pd.DataFrame({
    "Open": close - rng.uniform(0, 0.2, n),
    "High": close + rng.uniform(0.1, 0.5, n),
    "Low": close - rng.uniform(0.1, 0.5, n),
    "Close": close,
    "Volume": rng.uniform(1000, 8000, n),
  })


def test_run_smc_library():
  r = run_smc_library(_ohlcv(200), "1h")
  assert r.get("status") in ("ok", "unavailable", "error")


def test_cvd_and_divergence():
  df = _ohlcv(80)
  cvd = compute_cvd(df)
  assert len(cvd) == len(df)
  div = detect_cvd_divergence(df)
  assert div is None or div.startswith("cvd_")


def test_volume_profile():
  vp = compute_volume_profile(_ohlcv(60))
  assert vp.get("status") == "ok"
  assert "poc" in vp


def test_institutional_matrix():
  data = {"15m": _ohlcv(120), "1h": _ohlcv(120), "4h": _ohlcv(120)}
  m = build_institutional_matrix(data, "LONG")
  assert "institutional_score" in m
  assert "by_tf" in m


def test_detect_session_liquidity():
  idx = pd.date_range("2025-06-01", periods=10, freq="1h", tz="UTC")
  df = pd.DataFrame({"Close": range(10)}, index=idx)
  from core.institutional_edge import detect_session_liquidity
  r = detect_session_liquidity(df)
  assert r.get("status") == "ok"
  assert r.get("session") in ("asia", "london", "london_ny", "ny", "off_hours")


def test_build_smc_setup():
  data = {"15m": _ohlcv(120), "1h": _ohlcv(120), "4h": _ohlcv(120)}
  setup = build_smc_setup(
    "BTC/USDT", data, "LONG", 99, 101, False,
    {"consensus_direction": "BULL"},
    {"verdict": "STAGED_GO"},
  )
  assert setup["setup_type"] == "smc"
  assert setup["style"] == "smc"
  assert "status" in setup
  assert "entry_grade" in setup


def test_structure_blocks_counter_trend():
  assert structure_blocks_entry("choch_bear", "LONG") is True
  assert structure_blocks_entry("bos_bear", "LONG") is True
  assert structure_blocks_entry("choch_bull", "SHORT") is True
  assert structure_blocks_entry("choch_bull", "LONG") is False
  assert structure_blocks_entry("bos_bear", "SHORT") is False


def test_detect_entry_confirmation_rejection_wick_long():
  df = pd.DataFrame({
    "Open": [100.0, 100.0, 100.0, 99.5],
    "High": [101.0, 101.0, 100.8, 100.6],
    "Low": [99.0, 99.0, 98.5, 99.8],
    "Close": [100.5, 100.2, 100.4, 100.5],
    "Volume": [1000, 1000, 1000, 1000],
  })
  r = detect_entry_confirmation(df, "LONG", zone_top=100.5, zone_bot=99.0)
  assert r["confirmed"] is True
  assert r["mode"] == "rejection_wick"
