"""Tests for pre-execution multi-model consensus."""

from __future__ import annotations

from engine.execution_consensus import review_executable_rows, review_row


def _row(**kwargs):
  base = {
    "symbol": "BTC/USDT",
    "timeframe": "1h",
    "direction": "LONG",
    "executive_verdict": "CONDITIONAL_GO",
    "consensus": "BULL",
    "agreement_pct": 85,
    "engines_valid": 3,
    "wae": 100.0,
    "stop_loss": 98.0,
    "stop_distance_pct": 2.0,
    "dca_splits_pct": "10,20,30,40",
    "dca_profile": "pyramid_4",
    "position_notional_usd": 1000,
    "leg1_usd": 100,
  }
  base.update(kwargs)
  return base


def test_review_row_ew_bypass_agrees(monkeypatch):
  monkeypatch.setenv("EW_LLM_EW_BYPASS", "1")
  monkeypatch.setenv("EW_EXECUTION_CONSENSUS_LLM", "0")
  rev = review_row(_row(), use_llm=False)
  assert rev["allowed"] is True
  assert rev["stance"] in ("agree", "caution")


def test_review_row_rejects_low_agreement(monkeypatch):
  monkeypatch.setenv("EW_EXECUTION_CONSENSUS_LLM", "0")
  rev = review_row(_row(agreement_pct=25), use_llm=False)
  assert rev["allowed"] is False
  assert rev["stance"] == "reject"


def test_review_executable_batch(monkeypatch):
  monkeypatch.setenv("EW_EXECUTION_CONSENSUS_LLM", "0")
  rows = [_row(), _row(symbol="ETH/USDT", agreement_pct=20)]
  out = review_executable_rows(rows, use_llm=False)
  assert out["total"] == 2
  assert out["allowed"] == 1
  assert out["blocked"] == 1
