"""Tests for cheap-first LLM budget policy — 98% Cursor Pro / 2% Other Models."""

from __future__ import annotations

from engine.llm_budget_policy import (
  allow_premium_escalation,
  cheap_first_enabled,
  cheap_target_pct,
  cursor_pro_only,
  is_cursor_pro_model,
  is_other_quota_model,
  may_use_other_model,
  other_models_budget_pct,
  other_models_override,
  other_models_shame_pct,
  resolve_to_cursor_pro,
  routine_intelligence_mode,
)
from engine.llm_token_saver import get_pool_mix_tracker


def test_cheap_first_default_on():
  assert cheap_first_enabled() is True


def test_cheap_target_default_98():
  assert cheap_target_pct() == 98


def test_other_models_budget_default_2pct():
  assert other_models_budget_pct() == 2.0


def test_other_models_shame_default_5pct():
  assert other_models_shame_pct() == 5.0


def test_cursor_pro_only_default_on():
  assert cursor_pro_only() is True
  assert other_models_override() is False


def test_routine_mode_single_by_default():
  assert routine_intelligence_mode() == "single"


def test_cursor_pro_models():
  assert is_cursor_pro_model("composer-2.5")
  assert is_cursor_pro_model("cursor-grok-4.5-high")
  assert is_other_quota_model("gpt-5.6-sol")
  assert is_other_quota_model("claude-opus-4-8")
  assert not is_other_quota_model("composer-2.5")


def test_resolve_opus_to_grok_high():
  out = resolve_to_cursor_pro("claude-opus-4-8", task="executive")
  assert is_cursor_pro_model(out)
  assert "grok" in out.lower() or "composer" in out.lower()


def test_may_use_other_only_executive_go_high(monkeypatch):
  monkeypatch.setenv("EW_CURSOR_MODELS_ONLY", "0")
  monkeypatch.setenv("EW_USE_OTHER_MODEL_POOL", "1")
  stances = ["agree", "reject"]
  assert may_use_other_model("executive", "executive", "GO", "high", stances) is True
  assert may_use_other_model("planning", "executive", "GO", "high", stances) is False
  assert may_use_other_model("executive", "executive", "GO", "medium", stances) is False


def test_other_budget_blocks_after_2pct(monkeypatch):
  monkeypatch.setenv("EW_CURSOR_MODELS_ONLY", "0")
  monkeypatch.setenv("EW_USE_OTHER_MODEL_POOL", "1")
  tracker = get_pool_mix_tracker()
  monkeypatch.setattr(tracker, "_state", lambda: {"cursor_pro": 48, "other": 2})
  assert tracker.at_budget_limit() is True
  assert may_use_other_model("executive", "executive", "GO", "high", ["agree", "reject"]) is False


def test_shame_blocks_at_5pct(monkeypatch):
  tracker = get_pool_mix_tracker()
  monkeypatch.setattr(tracker, "_state", lambda: {"cursor_pro": 19, "other": 1})
  assert tracker.at_shame_limit() is True


def test_premium_blocked_for_non_executive(monkeypatch):
  monkeypatch.setenv("EW_CURSOR_MODELS_ONLY", "1")
  assert allow_premium_escalation(
    "architect", "GO", "high", ["agree", "reject"], context="self_improvement",
  ) is False
  assert allow_premium_escalation(
    "executive", "GO", "high", ["agree", "reject"], context="executive",
  ) is False


def test_premium_allowed_for_executive_when_other_pool_enabled(monkeypatch):
  monkeypatch.setenv("EW_CURSOR_MODELS_ONLY", "0")
  monkeypatch.setenv("EW_USE_OTHER_MODEL_POOL", "1")
  assert allow_premium_escalation(
    "executive", "GO", "high", ["agree", "reject"], context="executive",
  ) is True


def test_premium_allowed_when_override(monkeypatch):
  monkeypatch.setenv("EW_CURSOR_MODELS_ONLY", "0")
  monkeypatch.setenv("EW_ALLOW_OTHER_MODELS", "1")
  monkeypatch.setenv("EW_CURSOR_PRO_ONLY", "0")
  monkeypatch.setenv("EW_USE_OTHER_MODEL_POOL", "1")
  out = resolve_to_cursor_pro("claude-opus-4-8", task="planning")
  assert out == "claude-opus-4-8"
