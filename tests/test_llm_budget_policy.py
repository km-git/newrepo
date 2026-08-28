"""Tests for cheap-first LLM budget policy — 95% Cursor Pro target."""

from __future__ import annotations

from engine.llm_budget_policy import (
  allow_premium_escalation,
  cheap_first_enabled,
  cheap_target_pct,
  cursor_pro_only,
  is_cursor_pro_model,
  is_other_quota_model,
  other_models_allowed,
  resolve_to_cursor_pro,
  routine_intelligence_mode,
)


def test_cheap_first_default_on():
  assert cheap_first_enabled() is True


def test_cheap_target_default_95():
  assert cheap_target_pct() == 95


def test_cursor_pro_only_default_on():
  assert cursor_pro_only() is True
  assert other_models_allowed() is False


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


def test_premium_blocked_when_cursor_pro_only():
  assert allow_premium_escalation(
    "executive", "GO", "high", ["agree", "reject"], context="executive",
  ) is False
  assert allow_premium_escalation(
    "executive", "GO", "high", ["agree", "reject"], context="self_improvement",
  ) is False


def test_premium_allowed_when_other_models_enabled(monkeypatch):
  monkeypatch.setenv("EW_ALLOW_OTHER_MODELS", "1")
  monkeypatch.setenv("EW_CURSOR_PRO_ONLY", "0")
  assert allow_premium_escalation(
    "executive", "GO", "high", ["agree", "reject"], context="self_improvement",
  ) is True
