"""Tests for smart model roster and disagreement-aware escalation."""

from __future__ import annotations

from engine.llm_model_roster import (
  disagreement_severity,
  escalate_task_model,
  roster_summary,
  screen_model_slots,
  workhorse_model,
)


def test_disagreement_severity_mild():
  assert disagreement_severity(["agree", "caution"]) == "mild"
  assert disagreement_severity(["agree", "agree"]) == "none"


def test_disagreement_severity_hard():
  assert disagreement_severity(["agree", "reject"]) == "hard"
  assert disagreement_severity(["caution", "reject"]) == "hard"


def test_mild_disagreement_uses_terra_not_sol():
  model, tier, reason = escalate_task_model("tiebreaker", "GO", "high", ["agree", "caution"])
  assert model == "gpt-5.6-terra"
  assert tier == "standard"
  assert "Terra" in reason


def test_hard_disagreement_go_high_uses_opus():
  model, tier, _ = escalate_task_model("tiebreaker", "GO", "high", ["agree", "reject"])
  assert model == "claude-opus-4-8"
  assert tier == "flagship"


def test_hard_disagreement_default_uses_sol():
  model, tier, _ = escalate_task_model("tiebreaker", "NO_GO", "low", ["agree", "reject"])
  assert model == "gpt-5.6-sol"
  assert tier == "crucial"


def test_light_planning_uses_luna():
  model, tier, reason = escalate_task_model("planning", "CONDITIONAL_GO", "medium")
  assert model == "gpt-5.6-luna"
  assert tier == "standard"
  assert "luna" in reason.lower()


def test_full_planning_uses_sol():
  model, _, _ = escalate_task_model("planning", "GO", "high")
  assert model == "gpt-5.6-sol"


def test_workhorse_defaults_composer(monkeypatch):
  monkeypatch.delenv("EW_LLM_WORKHORSE_POOL", raising=False)
  assert workhorse_model() == "composer-2.5"


def test_screen_slots_dual_cheap():
  slots = screen_model_slots()
  assert len(slots) == 2
  models = {m for _, m in slots}
  assert "composer-2.5" in models
  assert "gpt-5-mini" in models


def test_roster_summary_has_efficiency_rules():
  summary = roster_summary()
  assert len(summary["models"]) >= 10
  assert any("Terra" in r for r in summary["efficiency_rules"])
