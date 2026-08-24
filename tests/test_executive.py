"""Tests for executive decision layer — always actionable output."""

from __future__ import annotations

import pandas as pd
import pytest

from engine.executive import executive_decide


def _mock_data(close: float = 64000.0) -> dict:
  n = 50
  idx = pd.date_range("2025-01-01", periods=n, freq="1d")
  base = pd.DataFrame(
    {"Open": close, "High": close * 1.01, "Low": close * 0.99, "Close": close, "Volume": 1e6},
    index=idx,
  )
  return {"1d": base, "15m": base}


def test_executive_never_no_trade():
  result = executive_decide(
    symbol="BTC/USDT",
    data=_mock_data(),
    htf_class={"state": "choppy", "bias": "neutral", "wave_A": {"start": 70000, "end": 60000}},
    kz_low=170000,
    kz_high=175000,
    prior_fibs={"fib_0.382": 63000, "fib_0.5": 62000, "fib_0.618": 61000},
    harmonic_overlaps=[],
    in_zone=False,
    execution_passes=False,
    exec_direction="BULL",
    bull_count=0,
    bear_count=1,
    violations_sample=["R1(W2=649%)"],
  )
  assert result["trade_setup"]["action"] != "no_trade"
  assert result["trade_setup"]["entry_zone"] is not None
  assert result["trade_setup"]["stop_loss"] is not None
  assert result["executive_decision"]["verdict"] in ("STAGED_GO", "CONDITIONAL_GO", "STANDBY_ORDERS", "GO")


def test_executive_full_execute_in_zone():
  result = executive_decide(
    symbol="BTC/USDT",
    data=_mock_data(close=172000),
    htf_class={"state": "correction_ABC", "bias": "bullish_reversal"},
    kz_low=171000,
    kz_high=173000,
    prior_fibs={},
    harmonic_overlaps=[{"pattern": "GARTLEY", "tf": "1h", "prz_low": 171500, "prz_high": 172500}],
    in_zone=True,
    execution_passes=True,
    exec_direction="BULL",
    bull_count=2,
    bear_count=0,
    violations_sample=[],
    mc_result={"empirical_probability": 0.6},
  )
  assert result["status"] == "execute"
  assert result["executive_decision"]["verdict"] == "GO"
  assert result["trade_setup"]["action"] == "execute_long"


def test_executive_staged_has_scale_legs():
  result = executive_decide(
    symbol="ETH/USDT",
    data=_mock_data(),
    htf_class={"state": "choppy", "bias": "bearish_reversal"},
    kz_low=4000,
    kz_high=4100,
    prior_fibs={"fib_0.5": 63800},
    harmonic_overlaps=[],
    in_zone=False,
    execution_passes=False,
    exec_direction="BEAR",
    bull_count=0,
    bear_count=2,
    violations_sample=["R2"],
  )
  assert result["status"] == "staged_entry"
  assert "scale_legs" in result["executive_decision"]
  legs = result["executive_decision"]["scale_legs"]
  assert len(legs) == 4
  assert [l["size_pct"] for l in legs] == [10, 20, 30, 40]
