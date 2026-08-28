"""Tests for smart model roster and disagreement-aware escalation."""

from __future__ import annotations

import pytest

from engine.llm_model_roster import (
  disagreement_severity,
  escalate_task_model,
  roster_summary,
  screen_model_slots,
  workhorse_model,
)


@pytest.fixture(autouse=True)
def _reset_governor():
  from engine.model_budget_governor import reset_governor

  reset_governor()
  yield
  reset_governor()


def _reload_roster(monkeypatch, **env):
  import importlib
  import engine.llm_model_roster as roster

  for key, val in env.items():
    monkeypatch.setenv(key, val)
  importlib.reload(roster)
  return roster


def test_disagreement_severity_mild():
  assert disagreement_severity(["agree", "caution"]) == "mild"
  assert disagreement_severity(["agree", "agree"]) == "none"


def test_disagreement_severity_hard():
  assert disagreement_severity(["agree", "reject"]) == "hard"
  assert disagreement_severity(["caution", "reject"]) == "hard"


def test_mild_disagreement_uses_grok_high_not_sol():
  model, tier, reason = escalate_task_model("tiebreaker", "GO", "high", ["agree", "caution"])
  assert model == "cursor-grok-4.5-high"
  assert tier == "standard"
  assert "Grok High" in reason


def test_mild_disagreement_falls_back_to_cursor_when_grok_disabled(monkeypatch):
  roster = _reload_roster(monkeypatch, EW_USE_GROK_HIGH="0", EW_MINIMIZE_GPT="1")
  model, tier, reason = roster.escalate_task_model("tiebreaker", "GO", "high", ["agree", "caution"])
  assert model in ("composer-2.5", "cursor-grok-4.5-high")
  assert "fallback" in reason.lower() or "composer" in reason.lower() or "terra" in reason.lower()


def test_hard_disagreement_go_high_uses_cursor_by_default():
  model, tier, _ = escalate_task_model("tiebreaker", "GO", "high", ["agree", "reject"])
  assert model == "cursor-grok-4.5-high"
  assert tier == "standard"


def test_hard_disagreement_go_high_uses_opus_when_other_pool_enabled(monkeypatch):
  from engine.model_budget_governor import ModelBudgetGovernor, reset_governor

  roster = _reload_roster(
    monkeypatch,
    EW_USE_OTHER_MODEL_POOL="1",
    EW_CURSOR_POOL_GOVERNOR="1",
    EW_MINIMIZE_GPT="0",
  )
  reset_governor()
  g = ModelBudgetGovernor()
  for _ in range(50):
    g.record_call("cheap", "composer-2.5")
  model, tier, _ = roster.escalate_task_model("tiebreaker", "GO", "high", ["agree", "reject"])
  assert model == "claude-opus-4-8"
  assert tier == "flagship"


def test_hard_disagreement_default_uses_cursor_grok():
  model, tier, _ = escalate_task_model("tiebreaker", "NO_GO", "low", ["agree", "reject"])
  assert model == "cursor-grok-4.5-high"
  assert tier == "standard"


def test_hard_disagreement_uses_cursor_for_non_executive(monkeypatch):
  roster = _reload_roster(
    monkeypatch,
    EW_USE_OTHER_MODEL_POOL="1",
    EW_CURSOR_POOL_GOVERNOR="0",
    EW_MINIMIZE_GPT="0",
  )
  model, tier, _ = roster.escalate_task_model("tiebreaker", "NO_GO", "low", ["agree", "reject"])
  assert model == "cursor-grok-4.5-high"
  assert tier == "standard"


def test_light_planning_uses_cursor_grok_by_default():
  model, tier, reason = escalate_task_model("planning", "CONDITIONAL_GO", "medium")
  assert model == "cursor-grok-4.5-high"
  assert tier == "standard"


def test_light_planning_stays_cursor_when_other_pool_enabled(monkeypatch):
  roster = _reload_roster(
    monkeypatch,
    EW_USE_OTHER_MODEL_POOL="1",
    EW_CURSOR_POOL_GOVERNOR="0",
    EW_MINIMIZE_GPT="0",
  )
  model, tier, _ = roster.escalate_task_model("planning", "CONDITIONAL_GO", "medium")
  assert model == "cursor-grok-4.5-high"
  assert tier == "standard"


def test_full_planning_uses_cursor_by_default():
  model, _, _ = escalate_task_model("planning", "GO", "high")
  assert model == "cursor-grok-4.5-high"


def test_workhorse_defaults_composer(monkeypatch):
  monkeypatch.delenv("EW_LLM_WORKHORSE_POOL", raising=False)
  assert workhorse_model() == "composer-2.5"


def test_screen_slots_default_cursor_pro_only():
  slots = screen_model_slots()
  assert len(slots) == 2
  models = {m for _, m in slots}
  assert "cursor-grok-4.5-high" in models
  assert "composer-2.5" in models
  assert "gpt-5-mini" not in models


def test_screen_slots_includes_gpt_when_other_pool_enabled(monkeypatch):
  roster = _reload_roster(
    monkeypatch,
    EW_USE_OTHER_MODEL_POOL="1",
    EW_CURSOR_ONLY_SCREEN="0",
    EW_CURSOR_PRO_ONLY="0",
    EW_ALLOW_OTHER_MODELS="1",
    EW_MINIMIZE_GPT="0",
  )
  slots = roster.screen_model_slots()
  models = {m for _, m in slots}
  assert "gpt-5-mini" in models


def test_screen_slots_falls_back_to_composer_without_grok(monkeypatch):
  monkeypatch.setenv("EW_USE_GROK_HIGH", "0")
  slots = screen_model_slots()
  models = {m for _, m in slots}
  assert "composer-2.5" in models


def test_roster_summary_has_efficiency_rules():
  summary = roster_summary()
  assert len(summary["models"]) >= 10
  assert any("10000" in r for r in summary["efficiency_rules"])
