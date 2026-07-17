"""Tests for LLM advisory on critical decisions."""

from __future__ import annotations

import json
from unittest.mock import patch

from engine.llm_advisor import (
  advisory_enabled,
  build_advisory_prompt,
  get_llm_advisory,
  is_critical_decision,
  maybe_advise_critical,
)


def test_is_critical_go():
  assert is_critical_decision("GO", {}) is True
  assert is_critical_decision("CONDITIONAL_GO", {}) is True
  assert is_critical_decision("STAGED_GO", {"honest_summary": {"probe_executable_count": 1}}) is True
  assert is_critical_decision("STANDBY_ORDERS", {"honest_summary": {"monitor_count": 4}}) is False


def test_advisory_enabled_env(monkeypatch):
  monkeypatch.delenv("EW_LLM_ADVISORY", raising=False)
  assert advisory_enabled() is False
  monkeypatch.setenv("EW_LLM_ADVISORY", "1")
  assert advisory_enabled() is True


def test_build_advisory_prompt_includes_verdict():
  p = build_advisory_prompt(
    "BTC/USDT",
    {"verdict": "GO", "direction": "BULL", "playbook": "enter", "structural_gaps": []},
    {"action": "execute_long", "entry_zone": [100, 101], "stop_loss": 95, "risk_reward": 2.0},
    {"1d": {"structure": "bull_impulse_5"}},
    {"consensus_direction": "BULL", "agreement_pct": 80},
    {"honest_summary": {"truth": "1 executable"}},
  )
  assert "GO" in p or '"v":"GO"' in p
  assert "BTC/USDT" in p or "BTC" in p


def test_maybe_advise_skips_non_critical():
  assert maybe_advise_critical(
    symbol="X/USDT",
    executive={"verdict": "STANDBY_ORDERS"},
    trade_setup={},
    wave_structure={},
    consensus={},
    outcomes={"honest_summary": {}},
    enabled=True,
  ) is None


@patch("engine.llm_advisor.call_openai_advisory")
@patch("engine.llm_advisor.call_anthropic_advisory")
@patch("engine.llm_advisor.routing_plan")
def test_get_llm_advisory_blends(mock_routes, mock_anthropic, mock_openai, monkeypatch, tmp_path):
  from cache.disk_cache import CompressedCache
  from cache import disk_cache

  monkeypatch.setenv("EW_LLM_INTELLIGENCE", "single")
  monkeypatch.setattr(disk_cache, "_global_cache", CompressedCache(cache_dir=tmp_path))
  mock_routes.return_value = [
    ("openai", "gpt-4o-mini", "cheap"),
    ("anthropic", "claude-3-5-haiku-20241022", "cheap"),
  ]
  mock_openai.return_value = {
    "available": True,
    "stance": "caution",
    "confidence_adjustment": -0.05,
    "summary": "Wave count weak on 1h.",
    "key_risks": ["R1 violation"],
    "sizing_note": "Half size.",
  }
  mock_anthropic.return_value = {
    "available": True,
    "stance": "agree",
    "confidence_adjustment": 0.02,
    "summary": "Structure aligns with HTF.",
    "key_risks": [],
    "sizing_note": "Normal size.",
  }

  result = get_llm_advisory(
    "BTC/USDT",
    {"verdict": "GO", "direction": "BULL", "conviction": "high", "playbook": "enter", "structural_gaps": []},
    {"action": "execute_long", "entry_zone": [100, 101], "stop_loss": 95, "risk_reward": 2.0, "confidence": 0.7},
    {"1d": {"structure": "bull_impulse_5"}},
    {"consensus_direction": "BULL", "agreement_pct": 80},
    {"honest_summary": {"truth": "1 full executable", "full_executable_count": 1}},
    use_cache=False,
  )

  assert result["consulted"] == ["openai", "anthropic"]
  assert result["consensus_stance"] == "caution"
  assert "token_budget" in result


@patch("engine.llm_advisor.call_openai_advisory")
@patch("engine.llm_advisor.call_anthropic_advisory")
def test_get_llm_advisory_ensemble_panel(mock_anthropic, mock_openai, monkeypatch, tmp_path):
  from cache.disk_cache import CompressedCache
  from cache import disk_cache

  monkeypatch.setenv("EW_LLM_INTELLIGENCE", "ensemble")
  monkeypatch.setenv("OPENAI_API_KEY", "sk-test")
  monkeypatch.setenv("ANTHROPIC_API_KEY", "sk-ant-test")
  monkeypatch.setattr(disk_cache, "_global_cache", CompressedCache(cache_dir=tmp_path))
  mock_openai.return_value = {
    "available": True,
    "stance": "agree",
    "confidence_adjustment": 0.02,
    "summary": "Aligned.",
  }
  mock_anthropic.return_value = {
    "available": True,
    "stance": "agree",
    "confidence_adjustment": 0.01,
    "summary": "Good structure.",
  }

  result = get_llm_advisory(
    "ETH/USDT",
    {"verdict": "GO", "direction": "BULL", "conviction": "high", "playbook": "enter", "structural_gaps": []},
    {"action": "execute_long", "entry_zone": [200, 201], "stop_loss": 190, "risk_reward": 2.0, "confidence": 0.7},
    {"1d": {"structure": "bull_impulse_5"}},
    {"consensus_direction": "BULL", "agreement_pct": 75},
    {"honest_summary": {"truth": "1 full executable", "full_executable_count": 1}},
    use_cache=False,
  )

  assert result["intelligence_panel"]["intelligence_mode"] == "ensemble"
  assert result["consensus_stance"] == "agree"
  assert "intelligence_panel" in result


@patch("engine.llm_advisor._call_advisory")
def test_get_llm_advisory_cursor_ensemble(mock_call, monkeypatch, tmp_path):
  from cache.disk_cache import CompressedCache
  from cache import disk_cache

  monkeypatch.setenv("EW_LLM_BACKEND", "cursor")
  monkeypatch.setenv("CURSOR_API_KEY", "crsr_test")
  monkeypatch.setenv("EW_LLM_INTELLIGENCE", "ensemble")
  monkeypatch.setattr(disk_cache, "_global_cache", CompressedCache(cache_dir=tmp_path))

  def _fake(provider, model, tier, prompt):
    return {
      "available": True,
      "backend": "cursor",
      "stance": "agree",
      "confidence_adjustment": 0.01,
      "summary": provider,
    }

  mock_call.side_effect = _fake

  result = get_llm_advisory(
    "SOL/USDT",
    {"verdict": "GO", "direction": "BULL", "conviction": "high", "playbook": "enter", "structural_gaps": []},
    {"action": "execute_long", "entry_zone": [100, 101], "stop_loss": 95, "risk_reward": 2.0, "confidence": 0.7},
    {"1d": {"structure": "bull_impulse_5"}},
    {"consensus_direction": "BULL", "agreement_pct": 75},
    {"honest_summary": {"truth": "1 full executable", "full_executable_count": 1}},
    use_cache=False,
  )

  assert result["llm_backend"] == "cursor"
  assert result["consensus_stance"] == "agree"
  assert mock_call.call_count >= 2
