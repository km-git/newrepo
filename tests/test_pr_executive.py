"""Tests for PR executive consensus (rule draft + AI mapping)."""

from __future__ import annotations

from engine.pr_executive import (
  apply_pr_ai_consensus,
  pr_actions_for_verdict,
  pr_draft_executive,
  pr_executive_consensus_enabled,
)


def _pr(**kwargs):
  base = {
    "number": 42,
    "title": "Add feature",
    "body": "Implements X with tests",
    "draft": False,
    "additions": 100,
    "deletions": 20,
    "changed_files": 3,
    "ci": {"pass": True, "fail": False, "pending": False},
    "files": [{"path": "tests/test_x.py"}],
    "labels": [],
  }
  base.update(kwargs)
  return base


def test_draft_approve_clean_pr():
  ex = pr_draft_executive(_pr())
  assert ex["verdict"] == "APPROVE_MERGE"
  assert ex["conviction"] == "high"


def test_draft_reject_ci_fail(monkeypatch):
  monkeypatch.setenv("EW_PR_REQUIRE_CI", "1")
  ex = pr_draft_executive(_pr(ci={"pass": False, "fail": True, "pending": False}))
  assert ex["verdict"] == "REJECT"


def test_draft_request_changes_when_draft():
  ex = pr_draft_executive(_pr(draft=True))
  assert ex["verdict"] == "REQUEST_CHANGES"


def test_ai_consensus_agree_upgrades_conditional(monkeypatch):
  monkeypatch.setenv("EW_PR_EXECUTIVE_CONSENSUS", "1")
  executive = {"verdict": "CONDITIONAL_MERGE", "playbook": "PR #1", "structural_gaps": []}
  panel = {
    "consensus_stance": "agree",
    "consulted": ["openai", "anthropic"],
    "intelligence_panel": {"escalated_to_premium": True},
    "blended_summary": "Looks good.",
  }
  final, actions = apply_pr_ai_consensus(executive, panel)
  assert final["verdict"] == "APPROVE_MERGE"
  assert final["verdict_source"] == "ai_consensus"
  assert actions["approve"] is True


def test_ai_consensus_reject_downgrades(monkeypatch):
  monkeypatch.setenv("EW_PR_EXECUTIVE_CONSENSUS", "1")
  executive = {"verdict": "APPROVE_MERGE", "playbook": "PR #1", "structural_gaps": []}
  panel = {"consensus_stance": "reject", "consulted": ["openai"], "intelligence_panel": {}}
  final, actions = apply_pr_ai_consensus(executive, panel)
  assert final["verdict"] == "REQUEST_CHANGES"


def test_actions_merge_on_approve_merge_agree(monkeypatch):
  monkeypatch.setenv("EW_PR_AUTO_APPROVE", "1")
  monkeypatch.setenv("EW_PR_AUTO_MERGE", "1")
  actions = pr_actions_for_verdict("APPROVE_MERGE", "agree", {"verdict": "APPROVE_MERGE"})
  assert actions["approve"] is True
  assert actions["merge"] is True


def test_actions_no_merge_on_caution(monkeypatch):
  monkeypatch.setenv("EW_PR_AUTO_MERGE", "1")
  actions = pr_actions_for_verdict("APPROVE_MERGE", "caution", {})
  assert actions["merge"] is False


def test_executive_consensus_enabled_default():
  assert pr_executive_consensus_enabled() is True
