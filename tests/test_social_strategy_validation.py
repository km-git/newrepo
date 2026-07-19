"""Tests for social intel and executive strategy validation."""

from __future__ import annotations

import json

import pytest

from engine.social_strategy_validation import (
  _build_validation_prompt,
  _rule_based_validation,
  run_social_strategy_validation,
)
from gateway.social_intel import (
  cross_reference_impact,
  scan_forum_mentions,
  social_intel_enabled,
)


def test_scan_forum_mentions():
  text = "rsi divergence on btc, supertrend flip, funding rate squeeze incoming"
  hits = scan_forum_mentions(text)
  ids = {h["id"] for h in hits}
  assert "rsi_divergence" in ids
  assert "supertrend_flip" in ids
  assert "funding_squeeze" in ids
  assert hits[0]["mention_count"] >= 1


def test_cross_reference_impact():
  candidates = [
    {
      "id": "supertrend_flip",
      "name": "Supertrend",
      "our_signal": "supertrend_aligned",
      "social_heat": 40,
      "mention_count": 5,
      "validation_prior": "needs_validation",
    }
  ]
  impact = {
    "discovery": {"baseline_wr": 0.61, "factors": []},
    "data_sources": [{"id": "supertrend_aligned", "inferred_lift": 0.06, "evidence": "TV OSS wired"}],
  }
  enriched = cross_reference_impact(candidates, impact)
  assert enriched[0]["measured_lift"] == 0.06


def test_rule_based_validation_promotes_measured_lift():
  candidates = [
    {"id": "a", "validation_prior": "likely_valid", "measured_lift": 0.12, "social_heat": 10},
    {"id": "b", "validation_prior": "likely_noise", "measured_lift": -0.15, "social_heat": 50},
  ]
  panel = _rule_based_validation(candidates)
  assert "a" in panel["validated"]
  assert "b" in panel["rejected"]
  assert panel["stance"] in ("agree", "caution")


def test_build_validation_prompt_includes_skeptic_questions():
  candidates = [
    {
      "id": "rsi_divergence",
      "name": "RSI Divergence",
      "validation_prior": "needs_validation",
      "social_heat": 30,
      "mention_count": 4,
      "measured_lift": None,
      "skeptic_q": "Is RSI lagging?",
    }
  ]
  prompt = _build_validation_prompt(candidates, symbol="BTC/USDT")
  assert "SKEPTIC Q" in prompt
  assert "rsi_divergence" in prompt
  assert "BTC/USDT" in prompt


def test_run_social_validation_offline(monkeypatch, tmp_path):
  monkeypatch.setenv("EW_SOCIAL_INTEL", "1")
  monkeypatch.setenv("EW_SOCIAL_VALIDATION", "1")

  from gateway import social_intel
  import engine.social_strategy_validation as ssv

  out = tmp_path / "social.json"
  monkeypatch.setattr(ssv, "VALIDATION_STATE", out)
  monkeypatch.setattr(social_intel, "_gather_social_text", lambda: ("", []))

  result = ssv.run_social_strategy_validation(use_llm=False)
  assert result.get("consensus_stance") in ("agree", "caution", "reject")
  assert result.get("candidates_reviewed", 0) >= 1
  assert out.exists()


def test_social_intel_disabled(monkeypatch):
  monkeypatch.setenv("EW_SOCIAL_INTEL", "0")
  from gateway.social_intel import build_social_intel

  assert build_social_intel()["available"] is False
