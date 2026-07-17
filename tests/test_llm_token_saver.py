"""Tests for token savers — per-model budget, EW bypass, registry."""

from __future__ import annotations

from engine.llm_token_saver import (
  PerModelTokenBudget,
  ew_consensus_aligns,
  should_bypass_llm_with_ew,
  structure_fingerprint,
  synthetic_panel_from_ew_consensus,
  token_saver_summary,
)
from engine.token_saver_registry import library_status, optimize_prompt_text, registry_summary


def test_structure_fingerprint_stable():
  ex = {"verdict": "GO", "direction": "BULL", "structural_gaps": ["gap1"]}
  cons = {"consensus_direction": "BULL", "agreement_pct": 80, "engines_valid": 3}
  wave = {"1d": {"structure": "bull_impulse_5"}, "4h": {"structure": "wave3"}}
  a = structure_fingerprint("BTC/USDT", ex, cons, wave)
  b = structure_fingerprint("BTC/USDT", ex, cons, wave)
  assert a == b


def test_ew_bypass_when_strong_consensus():
  executive = {"direction": "BULL", "verdict": "GO"}
  consensus = {"consensus_direction": "BULL", "agreement_pct": 80, "engines_valid": 2}
  assert should_bypass_llm_with_ew(executive, consensus) is True


def test_synthetic_panel_zero_tokens():
  result = synthetic_panel_from_ew_consensus(
    {"direction": "BULL", "verdict": "GO"},
    {"consensus_direction": "BULL", "agreement_pct": 90, "engines_valid": 3},
  )
  assert result["ew_bypass"] is True
  assert result["token_budget"]["est_total_tokens"] == 0


def test_per_model_budget_independent(tmp_path, monkeypatch):
  from cache.disk_cache import CompressedCache
  from cache import disk_cache

  monkeypatch.setenv("EW_LLM_MAX_TOKENS_PER_MODEL", "1000")
  monkeypatch.setattr(disk_cache, "_llm_cache", CompressedCache(cache_dir=tmp_path))
  budget = PerModelTokenBudget()

  budget.record("gpt-5-mini", 900)
  budget.record("claude-opus-4-8", 200)

  assert budget.used("gpt-5-mini") == 900
  assert budget.remaining("gpt-5-mini") == 100
  assert budget.used("claude-opus-4-8") == 200
  assert budget.remaining("claude-opus-4-8") == 800
  assert not budget.at_limit("claude-opus-4-8")


def test_per_model_budget_at_limit(tmp_path, monkeypatch):
  from cache.disk_cache import CompressedCache
  from cache import disk_cache

  monkeypatch.setenv("EW_LLM_MAX_TOKENS_PER_MODEL", "500")
  monkeypatch.setattr(disk_cache, "_llm_cache", CompressedCache(cache_dir=tmp_path))
  budget = PerModelTokenBudget()
  budget.record("composer-2.5", 500)
  assert budget.at_limit("composer-2.5")
  assert budget.cap_output("composer-2.5", "prompt", 100) == 0


def test_token_saver_summary_per_model():
  summary = token_saver_summary()
  assert summary["per_model_token_limit"] == 10000
  assert "model_budgets" in summary
  assert "registry" in summary


def test_registry_lists_libraries():
  reg = registry_summary()
  assert reg["total_count"] >= 8
  names = {l["name"] for l in reg["libraries"]}
  assert "tiktoken" in names
  assert "llm-token-optimizer" in names


def test_optimize_prompt_builtin_fallback():
  text = "hello   world\n\n\nfoo"
  optimized, meta = optimize_prompt_text(text)
  assert meta["optimized"] is True
  assert len(optimized) <= len(text)


def test_ew_consensus_aligns():
  assert ew_consensus_aligns({"direction": "BULL"}, {"consensus_direction": "BULL"}) is True
