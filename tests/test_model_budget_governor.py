"""Tests for 90/10 cheap/premium model budget governor."""

from __future__ import annotations

import pytest

from engine.model_budget_governor import (
  ModelBudgetGovernor,
  cheap_target_ratio,
  cheap_workhorse_route,
  cursor_target_ratio,
  is_cursor_pro_model,
  is_other_model,
  limit_cheap_routes,
  llm_allowed_for_routine,
  other_model_hard_ceiling,
  other_model_pool_enabled,
  other_model_shame_status,
  other_model_target_max,
  prefer_cursor_pool_model,
  purpose_for_brain_domain,
  should_escalate_to_premium,
  should_use_other_model,
)


@pytest.fixture(autouse=True)
def _reset_governor_state():
  from engine.model_budget_governor import reset_governor

  reset_governor()
  yield
  reset_governor()


def test_cheap_target_ratio_default():
  assert cheap_target_ratio() == 0.90


def test_routine_llm_off_by_default(monkeypatch):
  monkeypatch.delenv("EW_ROUTINE_LLM", raising=False)
  assert llm_allowed_for_routine() is False


def test_purpose_mapping():
  assert purpose_for_brain_domain("tv_oss") == "routine"
  assert purpose_for_brain_domain("risk") == "self_improvement"
  assert purpose_for_brain_domain("executive") == "executive"


def test_premium_blocked_for_routine():
  assert should_escalate_to_premium("routine", verdict="GO", conviction="high") is False
  assert should_escalate_to_premium("screen") is False


def test_premium_allowed_for_executive_go(tmp_path, monkeypatch):
  from engine.model_budget_governor import reset_governor

  monkeypatch.setenv("EW_MODEL_BUDGET_GOVERNOR", "1")
  monkeypatch.setenv("EW_PREMIUM_ESCALATION", "smart")
  monkeypatch.setenv("EW_LLM_CACHE_DIR", str(tmp_path))
  reset_governor()
  assert should_escalate_to_premium(
    "executive",
    verdict="GO",
    conviction="high",
    stances=["agree", "reject"],
  ) is True


def test_governor_tracks_cheap_ratio(tmp_path, monkeypatch):
  from engine.model_budget_governor import reset_governor

  monkeypatch.setenv("EW_LLM_CACHE_DIR", str(tmp_path))
  reset_governor()
  g = ModelBudgetGovernor()
  g.record_call("cheap", "composer-2.5")
  g.record_call("cheap", "grok-4.5")
  g.record_call("premium", "claude-opus-4-8")
  summary = g.summary()
  assert summary["cheap_calls"] == 2
  assert summary["premium_calls"] == 1
  assert summary["cheap_ratio"] >= 0.66


def test_limit_cheap_routes():
  routes = [
    ("openai", "m1", "cheap", "workhorse", 120),
    ("openai", "m2", "cheap", "workhorse", 120),
    ("openai", "m3", "cheap", "workhorse", 120),
    ("openai", "m4", "cheap", "workhorse", 120),
    ("openai", "m5", "cheap", "workhorse", 120),
    ("anthropic", "opus", "premium", "executive", 220),
  ]
  capped = limit_cheap_routes(routes, max_routes=3)
  assert len([r for r in capped if r[2] == "cheap"]) == 3
  assert any(r[1] == "opus" for r in capped)


def test_cheap_workhorse_route():
  provider, model, tier, task, max_out = cheap_workhorse_route()
  assert tier == "cheap"
  assert task == "workhorse"
  assert max_out > 0
  assert is_cursor_pro_model(model)


def test_cursor_target_ratio_default():
  assert cursor_target_ratio() == 0.98


def test_other_model_pool_off_by_default(monkeypatch):
  monkeypatch.delenv("EW_USE_OTHER_MODEL_POOL", raising=False)
  monkeypatch.delenv("EW_CURSOR_MODELS_ONLY", raising=False)
  assert other_model_pool_enabled() is False


def test_prefer_cursor_substitutes_gpt():
  model, sub = prefer_cursor_pool_model("gpt-5.6-sol", purpose="routine")
  assert sub is True
  assert is_cursor_pro_model(model)


def test_should_use_other_model_executive_only():
  assert should_use_other_model("routine") is False
  assert should_use_other_model("screen") is False
  assert should_use_other_model("self_improvement") is False


def test_governor_tracks_cursor_ratio(tmp_path, monkeypatch):
  from engine.model_budget_governor import reset_governor

  monkeypatch.setenv("EW_LLM_CACHE_DIR", str(tmp_path))
  reset_governor()
  g = ModelBudgetGovernor()
  g.record_call("cheap", "composer-2.5")
  g.record_call("cheap", "grok-4.5")
  g.record_call("premium", "claude-opus-4-8")
  summary = g.summary()
  assert summary["cursor_calls"] == 2
  assert summary["other_calls"] == 1
  assert summary["cursor_ratio"] >= 0.66
  assert is_other_model("claude-opus-4-8")


def test_ashamed_when_other_share_exceeds_target(monkeypatch):
  from engine.model_budget_governor import reset_governor

  monkeypatch.setenv("EW_CURSOR_POOL_GOVERNOR", "1")
  monkeypatch.setenv("EW_OTHER_MODEL_TARGET_MAX", "0.02")
  monkeypatch.setenv("EW_MIN_CURSOR_CALLS_BEFORE_OTHER", "1")
  reset_governor()
  g = ModelBudgetGovernor()
  for _ in range(2):
    g.record_call("cheap", "composer-2.5")
  g.record_call("premium", "claude-opus-4-8")
  assert g.is_ashamed() is True
  shame = other_model_shame_status()
  assert shame["ashamed"] is True
  assert shame["shame_events"] >= 1


def test_other_model_blocked_when_ashamed(monkeypatch):
  from engine.model_budget_governor import reset_governor

  monkeypatch.setenv("EW_CURSOR_POOL_GOVERNOR", "1")
  monkeypatch.setenv("EW_MIN_CURSOR_CALLS_BEFORE_OTHER", "1")
  reset_governor()
  g = ModelBudgetGovernor()
  g.record_call("cheap", "composer-2.5")
  g.record_call("premium", "claude-opus-4-8")
  assert should_use_other_model(
    "executive",
    verdict="GO",
    conviction="high",
    stances=["agree", "reject"],
    force_critical=True,
  ) is False


def test_other_model_allowed_under_budget_for_critical_executive(monkeypatch):
  from engine.model_budget_governor import reset_governor

  monkeypatch.setenv("EW_CURSOR_MODELS_ONLY", "0")
  monkeypatch.setenv("EW_USE_OTHER_MODEL_POOL", "1")
  monkeypatch.setenv("EW_CURSOR_POOL_GOVERNOR", "1")
  monkeypatch.setenv("EW_MIN_CURSOR_CALLS_BEFORE_OTHER", "50")
  reset_governor()
  g = ModelBudgetGovernor()
  for _ in range(50):
    g.record_call("cheap", "composer-2.5")
  assert should_use_other_model(
    "executive",
    verdict="GO",
    conviction="high",
    stances=["agree", "reject"],
    force_critical=True,
  ) is True


def test_other_model_hard_ceiling_blocks_at_five_percent(monkeypatch):
  from engine.model_budget_governor import reset_governor

  monkeypatch.setenv("EW_CURSOR_POOL_GOVERNOR", "1")
  monkeypatch.setenv("EW_MIN_CURSOR_CALLS_BEFORE_OTHER", "1")
  monkeypatch.setenv("EW_OTHER_MODEL_HARD_CEILING", "0.05")
  reset_governor()
  g = ModelBudgetGovernor()
  for _ in range(19):
    g.record_call("cheap", "composer-2.5")
  g.record_call("premium", "claude-opus-4-8")
  assert g.other_share() <= other_model_hard_ceiling() + 0.001
  assert should_use_other_model(
    "executive",
    verdict="GO",
    conviction="high",
    stances=["agree", "reject"],
    force_critical=True,
  ) is False


def test_other_model_target_defaults():
  assert other_model_target_max() == 0.02
  assert other_model_hard_ceiling() == 0.05
