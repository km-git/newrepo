"""Tests for autodream + honesty self-improvement via OKF brain."""

from __future__ import annotations

import pytest

from engine.brain_self_improve import (
  collect_autodream_lessons,
  collect_honesty_facts,
  persist_trading_cycle,
  recall_lessons,
  self_improve_enabled,
)


@pytest.fixture
def brain_dir(tmp_path, monkeypatch):
  monkeypatch.setenv("EW_OKF_BRAIN_DIR", str(tmp_path / "brain"))
  monkeypatch.setenv("EW_OKF_BRAIN", "1")
  monkeypatch.setenv("EW_BRAIN_CONSENSUS", "1")
  monkeypatch.setenv("EW_BRAIN_SELF_IMPROVE", "1")
  return tmp_path / "brain"


def _sample_outcomes():
  return {
    "honest_summary": {
      "truth": "0 full + 1 probe executable, 2 monitor, 1 skip — primary=swing (executable)",
      "primary_style": "swing",
      "primary_status": "executable",
      "primary_direction": "LONG",
      "full_executable_count": 0,
      "probe_executable_count": 1,
      "monitor_count": 2,
      "not_actionable_count": 1,
      "executive_verdict": "CONDITIONAL_GO",
    },
    "autodream": {
      "by_style": {
        "swing": {
          "lessons": ["swing: historical geometry favors TP-before-SL (58%)"],
          "win_rate": 0.58,
          "simulated_trades": 12,
        },
      },
      "history_entries": 5,
    },
    "setups": {},
  }


def test_collect_autodream_lessons():
  lessons = collect_autodream_lessons(_sample_outcomes())
  assert any("swing" in lesson for lesson in lessons)


def test_collect_honesty_facts():
  facts = collect_honesty_facts(_sample_outcomes(), {"hard_cap_applied": True})
  assert facts["probe_executable_count"] == 1
  assert facts["hard_cap_applied"] is True


def test_persist_trading_cycle(brain_dir):
  result = persist_trading_cycle(
    symbol="BTC/USDT",
    executive={"verdict": "CONDITIONAL_GO", "conviction": "medium", "playbook": "test"},
    outcomes=_sample_outcomes(),
    honesty_audit={"hard_cap_applied": True, "no_rule_relaxation": True},
    panel={"consensus_stance": "caution", "consulted": ["openai"]},
    pipeline_status="conditional_execute",
  )
  assert result["persisted"] is True
  assert result["improvement_path"]
  assert len(result.get("lessons", [])) >= 1


def test_recall_lessons_after_persist(brain_dir):
  persist_trading_cycle(
    symbol="ETH/USDT",
    executive={"verdict": "GO"},
    outcomes={
      "honest_summary": {"truth": "1 full executable"},
      "autodream": {"by_style": {"day_trade": {"lessons": ["day_trade: consistent LONG bias"]}}},
    },
    honesty_audit={},
    pipeline_status="execute",
  )
  recalled = recall_lessons("ETH/USDT")
  assert isinstance(recalled, list)


def test_self_improve_disabled(monkeypatch):
  monkeypatch.setenv("EW_BRAIN_SELF_IMPROVE", "0")
  assert self_improve_enabled() is False
