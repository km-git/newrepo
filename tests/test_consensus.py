"""Tests for multi-engine Elliott Wave consensus."""

from __future__ import annotations

import numpy as np
import pandas as pd
import pytest

from core.consensus import build_consensus
from core.ewa_adapter import scan_ewa
from core.taew_adapter import scan_taew_fib


def _sample_df(n: int = 120, trend: float = 1.0) -> pd.DataFrame:
  idx = pd.date_range("2025-01-01", periods=n, freq="D")
  close = 60000 + np.cumsum(np.random.default_rng(42).normal(trend, 200, n))
  high = close + 300
  low = close - 300
  return pd.DataFrame(
    {"Open": close, "High": high, "Low": low, "Close": close, "Volume": 1e6},
    index=idx,
  )


def _sample_mws_bull():
  return [
    {"type": "Up", "price_start": 60000, "price_end": 61000},
    {"type": "Down", "price_start": 61000, "price_end": 60500},
    {"type": "Up", "price_start": 60500, "price_end": 62000},
    {"type": "Down", "price_start": 62000, "price_end": 61200},
    {"type": "Up", "price_start": 61200, "price_end": 63000},
  ]


def test_taew_fib_on_valid_bull():
  result = scan_taew_fib(_sample_mws_bull())
  assert result["available"]
  assert result["direction"] == "BULL"
  assert "fib_score" in result


def test_ewa_scan_runs():
  df = _sample_df()
  result = scan_ewa(df, up_to=4, max_configs=30)
  assert result["available"]
  assert result["configs_tried"] > 0


def test_build_consensus_returns_votes():
  df = _sample_df()
  adaptive = {
    "1d": {"monowaves": _sample_mws_bull(), "skip": 3, "atr_14": 500},
    "4h": {"monowaves": _sample_mws_bull(), "skip": 3, "atr_14": 200},
    "15m": {"monowaves": _sample_mws_bull(), "skip": 3, "atr_14": 100},
  }
  data = {"1d": df, "4h": df, "15m": df}
  consensus = build_consensus(data, adaptive, "BTC/USDT")
  assert consensus["engines_run"] >= 4
  assert "consensus_direction" in consensus
  assert "votes" in consensus
  assert len(consensus["votes"]) >= 4
  assert "github_tools_used" in consensus
