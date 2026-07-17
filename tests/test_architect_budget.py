"""Tests for GPT-5.6 architect budget routing."""

from __future__ import annotations

import pytest

from engine.architect_budget import (
  ARCHITECT_TOKEN_CEILING,
  TokenBudgetExceeded,
  build_compact_prompt,
  cache_decision,
  count_tokens,
  get_cached_decision,
  prepare_decision_call,
  route_gpt56_decision,
  token_saver_checklist,
)


def test_count_tokens_positive():
  assert count_tokens("hello world") >= 2


def test_build_compact_prompt_within_ceiling():
  payload = {"isc": "Test MVP", "schema": {"users": "id"}}
  prompt, report = build_compact_prompt("architect", payload)
  assert report["within_budget"]
  assert report["est_total_tokens"] <= ARCHITECT_TOKEN_CEILING


def test_route_gpt56_for_architect():
  model, reason, use = route_gpt56_decision("architect")
  assert use
  assert "gpt-5.6" in model
  assert "10000" in reason or "10" in reason


def test_route_workhorse_for_unknown():
  # decision tasks use gpt; implementation would use workhorse via prepare_decision_call
  model, _, use = route_gpt56_decision("advise")
  assert use


def test_prepare_decision_call_budget():
  pkg = prepare_decision_call("decision", {"choice": "ship", "options": ["a", "b"]})
  assert pkg["budget"]["within_budget"]
  assert not pkg["skip_llm"]
  assert "gpt-5.6" in pkg["model"]


def test_cache_hit(tmp_path, monkeypatch):
  from cache import disk_cache
  from cache.disk_cache import CompressedCache

  monkeypatch.setattr(disk_cache, "_global_cache", CompressedCache(cache_dir=tmp_path))
  payload = {"isc": "cached test"}
  pkg1 = prepare_decision_call("architect", payload, use_cache=True)
  cache_decision("architect", pkg1["prompt"], {"isc": "cached test", "files": []})
  pkg2 = prepare_decision_call("architect", payload, use_cache=True)
  assert pkg2["skip_llm"]
  assert pkg2["budget"]["cache_hit"]


def test_enforce_budget_raises():
  from engine.architect_budget import enforce_budget_or_raise

  with pytest.raises(TokenBudgetExceeded):
    enforce_budget_or_raise({"within_budget": False, "est_total_tokens": 50_000, "ceiling": 10_000})


def test_token_savers_list():
  savers = token_saver_checklist()
  assert any("cache" in s.lower() for s in savers)
  assert any("10" in s for s in savers)
