"""Tests for PR panel vote tallying."""

from __future__ import annotations

from engine.pr_panel import (
  pr_min_approvals,
  stance_from_votes,
  tally_votes,
)


def test_tally_votes():
  responses = [
    {"stance": "agree"},
    {"stance": "agree"},
    {"stance": "agree"},
    {"stance": "agree"},
    {"stance": "agree"},
    {"stance": "caution"},
    {"stance": "reject"},
  ]
  t = tally_votes(responses)
  assert t["agree"] == 5
  assert t["total"] == 7


def test_stance_from_votes_5_of_7_approve(monkeypatch):
  monkeypatch.setenv("EW_PR_MIN_APPROVALS", "5")
  t = {"agree": 5, "caution": 1, "reject": 1}
  assert stance_from_votes(t) == "agree"


def test_stance_from_votes_reject_majority():
  t = {"agree": 2, "caution": 1, "reject": 4}
  assert stance_from_votes(t) == "reject"


def test_min_approvals_default():
  assert pr_min_approvals() == 5
