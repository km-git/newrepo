"""Tests for TV indicators, dynamic risk, and risk consensus."""

from __future__ import annotations

import numpy as np
import pandas as pd
import pytest


def _sample_ohlcv(n: int = 100, trend: float = 0.001) -> pd.DataFrame:
  rng = np.random.default_rng(42)
  close = 100 * np.cumprod(1 + rng.normal(trend, 0.01, n))
  high = close * (1 + rng.uniform(0, 0.01, n))
  low = close * (1 - rng.uniform(0, 0.01, n))
  return pd.DataFrame({
    "Open": close,
    "High": high,
    "Low": low,
    "Close": close,
    "Volume": rng.uniform(1000, 5000, n),
  })


def test_supertrend_direction():
  from core.tv_indicators import supertrend

  df = _sample_ohlcv(80, trend=0.002)
  st = supertrend(df)
  assert st["available"] is True
  assert st["direction"] in (1, -1)


def test_bollinger_pct_b():
  from core.tv_indicators import bollinger_bands

  bb = bollinger_bands(_sample_ohlcv(50))
  assert bb["available"] is True
  assert 0 <= bb["pct_b"] <= 1.5


def test_tv_confluence_long():
  from core.tv_indicators import score_tv_confluence

  df = _sample_ohlcv(100, trend=0.003)
  result = score_tv_confluence(df, "LONG")
  assert 0 <= result["score"] <= 100
  assert "signals" in result
  assert "layers" in result
  assert "trend" in result["layers"]


def test_chandelier_exit():
  from core.tv_indicators import chandelier_exit

  ch = chandelier_exit(_sample_ohlcv(60))
  assert ch["available"] is True
  assert ch["signal"] in ("bullish", "bearish", "neutral")


def test_ttm_squeeze():
  from core.tv_indicators import ttm_squeeze

  sq = ttm_squeeze(_sample_ohlcv(80))
  assert sq["available"] is True
  assert "squeeze_on" in sq


def test_hull_ma():
  from core.tv_indicators import hull_ma_trend

  hm = hull_ma_trend(_sample_ohlcv(50))
  assert hm["available"] is True


def test_tv_oss_catalog_complete():
  from core.tv_indicators import TV_OSS_CATALOG, compute_tv_signals

  assert len(TV_OSS_CATALOG) >= 8
  sig = compute_tv_signals(_sample_ohlcv(100))
  assert "chandelier" in sig
  assert "ttm_squeeze" in sig
  assert "hull_ma" in sig


def test_tv_oss_consensus_offline():
  from engine.tv_oss_consensus import run_tv_oss_consensus

  result = run_tv_oss_consensus(use_llm=False)
  assert result.get("consensus_stance") in ("agree", "caution", "reject")
  assert len(result.get("active_indicators", [])) >= 1
  assert "layer_weights" in result


def test_dynamic_risk_poor_history():
  from engine.dynamic_risk import compute_risk_multiplier

  ctx = compute_risk_multiplier(
    symbol="TEST/USDT",
    timeframe="1h",
    direction="LONG",
    hist_win_rate=0.30,
    hist_n=10,
    honest_tier="probe",
  )
  assert ctx["mult"] < 1.0
  assert any("hist_wr" in f for f in ctx["factors"])


def test_dynamic_risk_strong_history():
  from engine.dynamic_risk import compute_risk_multiplier

  ctx = compute_risk_multiplier(
    hist_win_rate=0.70,
    hist_n=12,
    tv_score=75,
    readiness_score=90,
    honest_tier="full",
  )
  assert ctx["mult"] >= 1.0


def test_risk_consensus_offline():
  from engine.risk_consensus import run_risk_consensus, summarize_tv_efficacy

  metrics = {
    "overall": {"win_rate": 0.61, "decided": 100, "wins": 61, "losses": 39},
    "open_count": 10,
    "by_timeframe": {
      "1w": {"win_rate": 0.51, "n": 50},
      "4h": {"win_rate": 0.68, "n": 30},
    },
  }
  summary = summarize_tv_efficacy(metrics)
  assert "tv_filters" in summary
  result = run_risk_consensus(metrics, use_llm=False)
  assert result.get("consensus_stance") in ("agree", "caution", "reject")
  assert "tv_summary" in result
