"""Tests for shared timeframe constants."""

from __future__ import annotations

from engine.timeframes import BOARD_TIMEFRAMES, CONTEXT_TIMEFRAMES, DEFAULT_TFS, UNIVERSE_TFS
from fetchers.ccxt_fetcher import TF_MAP


def test_tf_map_includes_12h():
  assert "12h" in TF_MAP
  assert TF_MAP["12h"] == "12h"


def test_context_timeframes():
  assert "4h" in CONTEXT_TIMEFRAMES
  assert "12h" in CONTEXT_TIMEFRAMES
  assert CONTEXT_TIMEFRAMES["12h"] == ("swing", "long_term")
