"""Tests for Phase 2: exchange wiring + calibration tokens."""

from __future__ import annotations

from engine.indicator_calibration import apply_extra_calibration_tokens, _default_token_weights
from core.market_tools import _funding_tokens, _orderbook_tokens, FUNDING_CROWDED_LONG


def test_funding_tokens():
  assert FUNDING_CROWDED_LONG in _funding_tokens(0.0005)
  assert _funding_tokens(0.0) == []


def test_orderbook_tokens():
  assert _orderbook_tokens(0.2) == ["orderbook bid pressure"]
  assert _orderbook_tokens(-0.2) == ["orderbook ask pressure"]


def test_apply_extra_calibration_tokens_uncalibrated():
  ind = {"score": 40, "threshold": 58, "signals": [], "active_tokens": []}
  out = apply_extra_calibration_tokens(
    ind, ["SMC BOS bull", "in bullish OB"], calibration={"available": False},
  )
  assert out["score"] > 40
  assert "SMC BOS bull" in out["active_tokens"]
