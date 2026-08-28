"""Tests for cheap-first LLM budget policy."""

from __future__ import annotations

from engine.llm_budget_policy import (
  allow_premium_escalation,
  cheap_first_enabled,
  cheap_target_pct,
  routine_intelligence_mode,
)


def test_cheap_first_default_on():
  assert cheap_first_enabled() is True


def test_cheap_target_default_90():
  assert cheap_target_pct() == 90


def test_routine_mode_single_by_default():
  assert routine_intelligence_mode() == "single"


def test_premium_blocked_for_routine_context():
  assert allow_premium_escalation("executive", "GO", "high", ["agree", "reject"], context="routine") is False


def test_premium_allowed_self_improvement_hard_disagree():
  assert allow_premium_escalation(
    "executive", "GO", "high", ["agree", "reject"], context="self_improvement",
  ) is True


def test_premium_executive_requires_go_high_hard(monkeypatch):
  monkeypatch.setenv("EW_CHEAP_FIRST", "1")
  assert allow_premium_escalation("executive", "GO", "high", ["agree", "reject"], context="executive") is True
  assert allow_premium_escalation("executive", "GO", "medium", ["agree", "reject"], context="executive") is False
  assert allow_premium_escalation("executive", "CONDITIONAL_GO", "high", ["agree", "reject"], context="executive") is False
