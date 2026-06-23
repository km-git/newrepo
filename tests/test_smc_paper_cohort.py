"""Tests for SMC paper cohort."""

from __future__ import annotations

import json
from pathlib import Path

import pandas as pd

from engine.smc_paper_cohort import (
  analyze_focus_token_lift,
  extract_smc_executables,
  run_smc_paper_cohort,
)
from engine.trade_simulation import SMC_COHORT_SIZE


def _smc_setup(tier="full", **kwargs):
  base = {
    "status": "executable",
    "execution_tier": tier,
    "direction": "LONG",
    "timeframe": "15m",
    "entry_grade": "A",
    "entry_signal": tier == "full",
    "institutional_score": 70,
    "entry": {"anchor": 100.0},
    "stop_loss": {"price": 98.0},
    "targets": [{"price": 103, "rr": 1.5}, {"price": 106, "rr": 3.0}],
    "indicators": {"calibrated": True, "active_tokens": ["liquidity sweep", "VP filter pass"]},
    "institutional": {"tags": ["MSB z-score pass"]},
  }
  base.update(kwargs)
  return base


def test_extract_smc_executables():
  results = [
    {"symbol": "BTC/USDT", "status": "active", "step8_outcomes": {
      "setups": {"smc": _smc_setup("full"), "swing": {"status": "monitor"}},
    }},
    {"symbol": "ETH/USDT", "status": "active", "step8_outcomes": {
      "setups": {"smc": _smc_setup("probe", entry_grade="B")},
    }},
    {"symbol": "X/USDT", "status": "active", "step8_outcomes": {
      "setups": {"smc": {"status": "monitor"}},
    }},
  ]
  rows = extract_smc_executables(results)
  assert len(rows) == 2
  assert rows[0]["execution_tier"] == "full"
  assert rows[1]["execution_tier"] == "probe"


def test_cohort_sizes():
  assert SMC_COHORT_SIZE["full"] == 0.50
  assert SMC_COHORT_SIZE["probe"] == 0.25


def test_analyze_focus_token_lift():
  ledger = []
  for i in range(20):
    win = i % 2 == 0
    tokens = ["liquidity sweep", "VP filter pass"] if i < 12 else ["MSB z-score weak"]
    ledger.append({
      "style": "smc",
      "cohort": "smc_paper",
      "paper_outcome": "win" if win else "loss",
      "indicator_tokens": tokens,
    })
  lift = analyze_focus_token_lift(ledger, cohort_only=True)
  assert lift["available"] is True
  assert "liquidity sweep" in lift["focus_tokens"]


def test_run_smc_paper_cohort_offline(monkeypatch):
  def fake_fetch(sym, tfs, is_crypto=True):
    n = 60
    close = [100 + i * 0.1 for i in range(n)]
    df = pd.DataFrame({
      "Open": close, "High": [c + 0.5 for c in close],
      "Low": [c - 0.5 for c in close], "Close": close,
      "Volume": [1000] * n,
    })
    return {"15m": df, "1h": df}

  monkeypatch.setattr("engine.smc_paper_cohort._fetch_symbol_data", fake_fetch)
  results = [{
    "symbol": "TEST/USDT",
    "status": "active",
    "step8_outcomes": {"setups": {"smc": _smc_setup("full")}},
  }]
  report = run_smc_paper_cohort(results, fetch_missing=True)
  assert report["full_count"] == 1
  assert report["trades"][0]["cohort_size_pct"] == 50.0
  assert report["trades"][0].get("cohort") == "smc_paper"
