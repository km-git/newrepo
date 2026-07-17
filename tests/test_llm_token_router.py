"""Tests for token-efficient LLM routing."""

from __future__ import annotations

import json

from engine.llm_token_router import (
  build_compact_prompt,
  compact_advisory_payload,
  estimate_tokens,
  model_for,
  routing_plan,
  select_providers,
  tier_for_verdict,
  token_budget_report,
)


def test_compact_prompt_smaller_than_legacy(monkeypatch):
  monkeypatch.delenv("EW_LLM_TIER", raising=False)
  payload = compact_advisory_payload(
    "BTC/USDT",
    {"verdict": "GO", "direction": "BULL", "conviction": "high", "structural_gaps": ["gap1", "gap2"]},
    {"action": "execute_long", "entry_zone": [100, 101], "stop_loss": 95, "take_profit_1": 110, "risk_reward": 2.0, "confidence": 0.7},
    {"1d": {"structure": "bull_impulse_5"}, "4h": {"structure": "abc_correction"}},
    {"consensus_direction": "BULL", "agreement_pct": 80, "engines_valid": 2},
    {"honest_summary": {"truth": "1 full executable", "full_executable_count": 1}},
  )
  compact = build_compact_prompt(payload)
  legacy = (
    "You are a senior risk manager reviewing an algorithmic Elliott Wave trade plan.\n"
    f"TRADE PACKET:\n{json.dumps(payload, indent=2)}"
  )
  assert len(compact) < len(legacy)
  assert '"sym":"BTC/USDT"' in compact or '"sym": "BTC/USDT"' in compact


def test_auto_selects_single_provider(monkeypatch):
  monkeypatch.setenv("EW_LLM_PROVIDER", "auto")
  monkeypatch.setenv("OPENAI_API_KEY", "sk-test")
  monkeypatch.delenv("ANTHROPIC_API_KEY", raising=False)
  assert select_providers() == ["openai"]


def test_dual_selects_both(monkeypatch):
  monkeypatch.setenv("EW_LLM_PROVIDER", "dual")
  monkeypatch.setenv("OPENAI_API_KEY", "sk-test")
  monkeypatch.setenv("ANTHROPIC_API_KEY", "sk-ant-test")
  assert select_providers() == ["openai", "anthropic"]


def test_cheap_tier_default(monkeypatch):
  monkeypatch.delenv("EW_LLM_TIER", raising=False)
  monkeypatch.delenv("EW_LLM_PREMIUM_GO", raising=False)
  assert tier_for_verdict("CONDITIONAL_GO") == "cheap"
  assert tier_for_verdict("GO", "high") == "cheap"


def test_routing_plan_single_route(monkeypatch):
  monkeypatch.setenv("EW_LLM_PROVIDER", "openai")
  monkeypatch.setenv("OPENAI_API_KEY", "sk-test")
  routes = routing_plan("GO", "high")
  assert len(routes) == 1
  assert routes[0][0] == "openai"
  assert routes[0][1] == model_for("openai", "cheap")


def test_token_budget_report():
  prompt = "x" * 400
  routes = [("openai", "gpt-4o-mini", "cheap")]
  report = token_budget_report(prompt, routes)
  assert report["est_input_tokens"] == 100
  assert report["provider_mode"] in ("auto", "openai", "dual", "anthropic")
