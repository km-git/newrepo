"""Tests for AI consensus executive decision layer."""

from __future__ import annotations

from engine.llm_executive import (
  apply_ai_consensus_to_decision,
  apply_ai_consensus_to_executive,
  executive_consensus_enabled,
)


def _draft_decision(verdict: str = "GO") -> dict:
  return {
    "status": "execute",
    "trade_setup": {
      "action": "execute_long",
      "confidence": 0.72,
      "reason": "full confluence",
      "entry_zone": [100, 101],
      "stop_loss": 95,
    },
    "executive_decision": {
      "verdict": verdict,
      "conviction": "high",
      "direction": "BULL",
      "position_size_pct": 100,
      "playbook": "Enter now",
      "structural_gaps": [],
    },
  }


def _panel(stance: str, escalated: bool = False) -> dict:
  return {
    "consensus_stance": stance,
    "confidence_adjustment": -0.05 if stance == "caution" else 0.02,
    "consulted": ["openai", "anthropic"],
    "intelligence_mode": "ensemble",
    "intelligence_panel": {"escalated_to_premium": escalated},
  }


def test_agree_keeps_go_verdict():
  exec_out, trade, status = apply_ai_consensus_to_executive(
    _draft_decision()["executive_decision"],
    _draft_decision()["trade_setup"],
    _panel("agree"),
    "execute",
  )
  assert exec_out["verdict"] == "GO"
  assert exec_out["draft_verdict"] == "GO"
  assert exec_out["verdict_source"] == "ai_consensus"
  assert status == "execute"
  assert trade["action"] == "execute_long"


def test_caution_downgrades_go_to_conditional():
  exec_out, trade, status = apply_ai_consensus_to_executive(
    _draft_decision()["executive_decision"],
    _draft_decision()["trade_setup"],
    _panel("caution"),
    "execute",
  )
  assert exec_out["verdict"] == "CONDITIONAL_GO"
  assert status == "conditional_execute"
  assert trade["action"] == "conditional_long"
  assert exec_out["position_size_pct"] == 50


def test_reject_downgrades_go_to_staged():
  exec_out, trade, status = apply_ai_consensus_to_executive(
    _draft_decision()["executive_decision"],
    _draft_decision()["trade_setup"],
    _panel("reject"),
    "execute",
  )
  assert exec_out["verdict"] == "STAGED_GO"
  assert status == "staged_entry"
  assert trade["action"] == "scale_long"
  assert exec_out["position_size_pct"] <= 30


def test_agree_with_tiebreaker_upgrades_conditional_to_go():
  exec_out, _, status = apply_ai_consensus_to_executive(
    _draft_decision("CONDITIONAL_GO")["executive_decision"],
    _draft_decision("CONDITIONAL_GO")["trade_setup"],
    _panel("agree", escalated=True),
    "conditional_execute",
  )
  assert exec_out["verdict"] == "GO"
  assert status == "execute"


def test_apply_to_full_decision():
  out = apply_ai_consensus_to_decision(_draft_decision(), _panel("caution"))
  assert out["executive_decision"]["verdict"] == "CONDITIONAL_GO"
  assert out["status"] == "conditional_execute"


def test_executive_consensus_enabled_by_default(monkeypatch):
  monkeypatch.delenv("EW_LLM_EXECUTIVE_CONSENSUS", raising=False)
  assert executive_consensus_enabled() is True


def test_executive_consensus_can_disable(monkeypatch):
  monkeypatch.setenv("EW_LLM_EXECUTIVE_CONSENSUS", "0")
  assert executive_consensus_enabled() is False
