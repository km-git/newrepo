"""Tests for TV OSS dynamic discovery and exploration indicators."""

from __future__ import annotations

import numpy as np
import pandas as pd


def _sample(n=100):
  rng = np.random.default_rng(7)
  close = 100 * np.cumprod(1 + rng.normal(0.001, 0.01, n))
  return pd.DataFrame({
    "Open": close,
    "High": close * 1.01,
    "Low": close * 0.99,
    "Close": close,
    "Volume": rng.uniform(1000, 5000, n),
  })


def test_chaikin_mf():
  from core.tv_indicators import chaikin_mf

  r = chaikin_mf(_sample())
  assert r["available"] is True
  assert "signal" in r


def test_williams_r():
  from core.tv_indicators import williams_r

  r = williams_r(_sample())
  assert r["available"] is True
  assert -100 <= r["value"] <= 0


def test_aroon():
  from core.tv_indicators import aroon

  r = aroon(_sample(80))
  assert r["available"] is True


def test_exploration_signals():
  from core.tv_indicators import compute_exploration_signals

  sig = compute_exploration_signals(_sample())
  assert "cmf" in sig
  assert "wavetrend" in sig


def test_explore_candidates_ranked():
  from engine.tv_oss_discovery import explore_candidates

  ranked = explore_candidates(_sample(), direction="LONG")
  assert len(ranked) >= 4
  assert ranked[0]["dynamic_value"] >= ranked[-1]["dynamic_value"]


def test_run_discovery_offline(tmp_path, monkeypatch):
  import engine.tv_oss_discovery as disc

  monkeypatch.setattr(disc, "DISCOVERY_STATE", tmp_path / "disc.json")
  result = disc.run_tv_oss_discovery(use_llm=False)
  assert result.get("candidates_explored", 0) >= 1
  assert (tmp_path / "disc.json").exists()
