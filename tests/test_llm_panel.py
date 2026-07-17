"""Tests for multi-model intelligence panel."""

from __future__ import annotations

from engine.llm_panel import (
  apply_panel_to_trade,
  blend_stances,
  effective_intelligence_mode,
  models_disagree,
  run_panel,
)


def test_effective_mode_falls_back_without_both_keys(monkeypatch):
  monkeypatch.setenv("EW_LLM_INTELLIGENCE", "ensemble")
  monkeypatch.setenv("OPENAI_API_KEY", "sk-test")
  monkeypatch.delenv("ANTHROPIC_API_KEY", raising=False)
  assert effective_intelligence_mode() == "single"


def test_models_disagree_reject_vs_agree():
  assert models_disagree([
    {"stance": "agree"},
    {"stance": "reject"},
  ]) is True


def test_models_agree_no_disagreement():
  assert models_disagree([
    {"stance": "agree"},
    {"stance": "agree"},
  ]) is False


def test_blend_stances_tiebreaker_wins():
  assert blend_stances(
    [{"stance": "agree"}, {"stance": "reject"}],
    {"stance": "caution"},
  ) == "caution"


def test_run_panel_escalates_on_disagreement(monkeypatch):
  monkeypatch.setenv("EW_LLM_INTELLIGENCE", "ensemble")
  monkeypatch.setenv("OPENAI_API_KEY", "sk-test")
  monkeypatch.setenv("ANTHROPIC_API_KEY", "sk-ant-test")

  calls = []

  def fake_call(provider, model, tier):
    calls.append((provider, model, tier))
    if tier == "cheap":
      stance = "agree" if provider == "openai" else "reject"
      return {"available": True, "stance": stance, "confidence_adjustment": 0.0, "summary": provider}
    return {"available": True, "stance": "caution", "confidence_adjustment": -0.03, "summary": "tiebreak"}

  panel = run_panel("prompt", "GO", "high", fake_call)

  assert panel["disagreement"] is True
  assert panel["escalated_to_premium"] is True
  assert panel["consensus_stance"] == "caution"
  assert panel["tiebreaker"] is not None
  assert len([c for c in calls if c[2] == "cheap"]) == 2
  assert len([c for c in calls if c[2] == "standard"]) == 1


def test_run_panel_no_escalation_when_unanimous(monkeypatch):
  monkeypatch.setenv("EW_LLM_INTELLIGENCE", "ensemble")
  monkeypatch.setenv("OPENAI_API_KEY", "sk-test")
  monkeypatch.setenv("ANTHROPIC_API_KEY", "sk-ant-test")

  def fake_call(provider, model, tier):
    return {"available": True, "stance": "agree", "confidence_adjustment": 0.02, "summary": "ok"}

  panel = run_panel("prompt", "GO", "medium", fake_call)
  assert panel["disagreement"] is False
  assert panel["escalated_to_premium"] is False
  assert panel["consensus_stance"] == "agree"


def test_apply_panel_to_trade_adjusts_confidence():
  trade = apply_panel_to_trade(
    {"confidence": 0.7, "action": "execute_long"},
    {"consensus_stance": "caution", "confidence_adjustment": -0.05},
  )
  assert trade["confidence"] == 0.65
  assert trade["confidence_before_panel"] == 0.7
  assert trade["panel_note"]


def test_apply_panel_reject_warning():
  trade = apply_panel_to_trade(
    {"confidence": 0.6},
    {"consensus_stance": "reject", "confidence_adjustment": -0.1},
  )
  assert trade["panel_warning"]
