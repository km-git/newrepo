"""Tests for brain consensus orchestrator."""

from __future__ import annotations

import pytest

from engine.brain_consensus import ask_brain, brain_consensus_enabled, record_decision


@pytest.fixture
def brain_dir(tmp_path, monkeypatch):
  monkeypatch.setenv("EW_OKF_BRAIN_DIR", str(tmp_path / "brain"))
  monkeypatch.setenv("EW_OKF_BRAIN", "1")
  monkeypatch.setenv("EW_BRAIN_CONSENSUS", "1")
  monkeypatch.setenv("EW_BRAIN_LLM", "0")
  return tmp_path / "brain"


def test_ask_brain_without_llm(brain_dir):
  result = ask_brain("Should we scale into BTC swing?", use_llm=False)
  assert result["question"]
  assert result["stance"] in ("unknown", "caution", "agree", "reject")
  assert result["okf"].get("persisted") is True


def test_record_decision(brain_dir):
  out = record_decision(
    domain="trading",
    subject="BTC GO",
    verdict="GO",
    stance="agree",
    panel={"consensus_stance": "agree"},
  )
  assert out.get("persisted") is True


def test_brain_consensus_disabled(monkeypatch):
  monkeypatch.setenv("EW_BRAIN_CONSENSUS", "0")
  assert brain_consensus_enabled() is False


def test_ask_brain_includes_context(brain_dir, monkeypatch):
  monkeypatch.setenv("EW_BRAIN_LLM", "0")
  result = ask_brain(
    "Should we tighten risk?",
    use_llm=False,
    context="RISK METRICS: win_rate=0.62 n=40",
  )
  assert result["stance"] in ("unknown", "caution", "agree", "reject")


def test_ask_brain_stub_when_no_credentials(brain_dir, monkeypatch):
  monkeypatch.setenv("EW_BRAIN_LLM", "1")
  monkeypatch.setattr("engine.llm_advisor.advisory_credentials_available", lambda: False)
  result = ask_brain("Probe sizing?", use_llm=True)
  assert result["stance"] == "caution"
  assert result["panel"].get("intelligence_mode") == "stub"


def test_make_prompt_call_provider_passes_prompt(monkeypatch):
  seen = {}

  def fake_call(provider, model, tier, task, max_out, prompt):
    seen["prompt"] = prompt
    return {"available": True, "stance": "agree", "summary": "ok"}

  monkeypatch.setattr("engine.llm_advisor.advisory_credentials_available", lambda: True)
  monkeypatch.setattr("engine.llm_advisor._call_advisory", fake_call)

  from engine.brain_consensus import make_prompt_call_provider

  provider = make_prompt_call_provider("DOMAIN CONTEXT\n\nQUESTION: test")
  provider("openai", "gpt-test", "cheap", "screen", 256)
  assert seen["prompt"] == "DOMAIN CONTEXT\n\nQUESTION: test"
