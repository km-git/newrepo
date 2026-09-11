"""Tests for TV microstructure order-flow indicators."""

from __future__ import annotations

import numpy as np
import pandas as pd


def _df(n=80):
  rng = np.random.default_rng(11)
  close = 100 * np.cumprod(1 + rng.normal(0.0008, 0.012, n))
  return pd.DataFrame({
    "Open": close * 0.999,
    "High": close * 1.008,
    "Low": close * 0.992,
    "Close": close,
    "Volume": rng.uniform(5000, 20000, n),
  })


def test_cvd_available():
  from core.tv_microstructure import cumulative_volume_delta

  r = cumulative_volume_delta(_df())
  assert r["available"] is True
  assert "cvd_slope" in r


def test_volume_profile_poc():
  from core.tv_microstructure import volume_profile

  r = volume_profile(_df())
  assert r["available"] is True
  assert r["poc"] > 0
  assert r["val"] <= r["poc"] <= r["vah"] or r["val"] <= r["vah"]


def test_tpo_profile():
  from core.tv_microstructure import tpo_profile

  r = tpo_profile(_df())
  assert r["available"] is True


def test_anchored_vwap():
  from core.tv_microstructure import anchored_vwap

  r = anchored_vwap(_df())
  assert r["available"] is True
  assert r["avwap"] > 0


def test_hidden_liquidity_from_book():
  from core.tv_microstructure import hidden_liquidity_proxy

  r = hidden_liquidity_proxy({"available": True, "imbalance": 0.35, "bid_vol": 100, "ask_vol": 50})
  assert r["signal"] == "hidden_bid_wall"


def test_microstructure_bundle():
  from core.tv_microstructure import compute_microstructure_signals, score_microstructure_confluence

  ms = compute_microstructure_signals(_df())
  assert ms["cvd"]["available"]
  assert ms["volume_profile"]["available"]
  score = score_microstructure_confluence(ms, "LONG")
  assert 0 <= score["score"] <= 100


def test_tv_signals_include_microstructure():
  from core.tv_indicators import compute_tv_signals

  sig = compute_tv_signals(_df())
  assert "microstructure" in sig
  assert sig["microstructure"]["cvd"]["available"]
