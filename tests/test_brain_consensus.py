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
