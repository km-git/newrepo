"""Tests for token savers — EW bypass, structure fingerprint, session budget."""

from __future__ import annotations

from engine.llm_token_saver import (
  SessionTokenBudget,
  ew_consensus_aligns,
  ew_consensus_strong_enough,
  get_session_budget,
  llm_cache_ttl,
  should_bypass_llm_with_ew,
  structure_fingerprint,
  synthetic_panel_from_ew_consensus,
  token_saver_summary,
)


def test_structure_fingerprint_stable():
  ex = {"verdict": "GO", "direction": "BULL", "structural_gaps": ["gap1"]}
  cons = {"consensus_direction": "BULL", "agreement_pct": 80, "engines_valid": 3}
  wave = {"1d": {"structure": "bull_impulse_5"}, "4h": {"structure": "wave3"}}
  a = structure_fingerprint("BTC/USDT", ex, cons, wave)
  b = structure_fingerprint("BTC/USDT", ex, cons, wave)
  assert a == b
  assert len(a) == 16


def test_ew_bypass_when_strong_consensus():
  executive = {"direction": "BULL", "verdict": "GO"}
  consensus = {"consensus_direction": "BULL", "agreement_pct": 80, "engines_valid": 2}
  assert should_bypass_llm_with_ew(executive, consensus) is True


def test_ew_bypass_disabled(monkeypatch):
  monkeypatch.setenv("EW_LLM_EW_BYPASS", "0")
  executive = {"direction": "BULL"}
  consensus = {"consensus_direction": "BULL", "agreement_pct": 90, "engines_valid": 3}
  assert should_bypass_llm_with_ew(executive, consensus) is False


def test_synthetic_panel_zero_tokens():
  result = synthetic_panel_from_ew_consensus(
    {"direction": "BULL", "verdict": "GO"},
    {"consensus_direction": "BULL", "agreement_pct": 90, "engines_valid": 3, "github_tools_used": ["ewa"]},
  )
  assert result["ew_bypass"] is True
  assert result["token_budget"]["est_total_tokens"] == 0


def test_session_budget_tracks_usage(tmp_path, monkeypatch):
  from cache.disk_cache import CompressedCache
  from cache import disk_cache

  monkeypatch.setenv("EW_LLM_MAX_SESSION_TOKENS", "1000")
  monkeypatch.setattr(disk_cache, "_llm_cache", CompressedCache(cache_dir=tmp_path))
  budget = SessionTokenBudget()
  assert budget.remaining() == 1000
  budget.record(400)
  assert budget.used() == 400
  assert budget.remaining() == 600
  assert budget.can_spend(500) is True
  assert budget.can_spend(700) is False


def test_session_budget_caps_output(tmp_path, monkeypatch):
  from cache.disk_cache import CompressedCache
  from cache import disk_cache

  monkeypatch.setenv("EW_LLM_MAX_SESSION_TOKENS", "500")
  monkeypatch.setattr(disk_cache, "_llm_cache", CompressedCache(cache_dir=tmp_path))
  budget = SessionTokenBudget()
  budget.record(450)
  capped = budget.cap_output("short prompt", 200)
  assert capped < 200
  assert capped >= 0


def test_llm_cache_ttl_default():
  assert llm_cache_ttl() == 14400


def test_token_saver_summary():
  summary = token_saver_summary()
  assert summary["session_token_limit"] == 10000
  assert summary["ew_bypass"] is True
  assert "tiktoken" in summary["libraries"][0] or summary["tiktoken"] is not None
