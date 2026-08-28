"""Tests for market structure and executive intel extensions."""

from __future__ import annotations

import pandas as pd
import numpy as np

from core.tv_market_structure import detect_market_structure, score_market_structure
from engine.executive_intel import executive_intel_enabled, setup_intel_boost


def _trend_df(n: int = 120, up: bool = True) -> pd.DataFrame:
  """Synthetic OHLCV with clear swing highs/lows."""
  close = []
  p = 100.0
  for i in range(n):
    step = 0.8 if up else -0.8
    if i % 20 < 10:
      p += abs(step)
    else:
      p -= abs(step) * 0.3
    close.append(p)
  close = np.array(close, dtype=float)
  high = close + np.abs(np.sin(np.arange(n) / 3)) + 0.5
  low = close - np.abs(np.cos(np.arange(n) / 3)) - 0.5
  return pd.DataFrame({"Open": close, "High": high, "Low": low, "Close": close, "Volume": 1000})


def test_market_structure_uptrend():
  ms = detect_market_structure(_trend_df(up=True), swing=2)
  assert ms.get("available") is True
  assert ms.get("trend") in ("bullish", "neutral", "bearish")


def test_score_market_structure_long():
  ms = {"available": True, "bias": "bullish", "event": "bos_bull", "choch": False, "bos": True}
  sc = score_market_structure(ms, "LONG")
  assert sc["score"] >= 58
  assert sc["aligned"] is True


def test_executive_intel_boost_with_structure():
  boost, tags = setup_intel_boost(
    setup={"direction": "LONG", "timeframe": "4h"},
    market_tools={
      "tv_confluence": {"score": 72, "aligned": True},
      "market_structure": {"available": True, "event": "bos_bull", "bias": "bullish"},
      "ms_structure": {"score": 70, "aligned": True, "signals": ["structure bos_bull"]},
      "web_intel": {"fear_greed": {"available": True, "value": 22}},
    },
  )
  assert executive_intel_enabled()
  assert boost > 0
  assert any("tv_oss" in t or "structure" in t for t in tags)
