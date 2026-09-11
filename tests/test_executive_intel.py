"""Tests for executive intel layer (TV OSS + free data → scoring)."""

from __future__ import annotations

from engine.executive_intel import (
  executive_intel_enabled,
  global_risk_adjustment,
  setup_intel_boost,
)


def test_executive_intel_enabled_default():
  assert executive_intel_enabled() is True


def test_setup_intel_boost_capped():
  boost, tags = setup_intel_boost(
    setup={"direction": "LONG", "indicators": {"tv_score": 99, "tv_aligned": True}},
    market_tools={
      "web_intel": {"fear_greed": {"available": True, "value": 10}},
      "ws": {"imbalance": 0.3},
      "confluence_boost": 20,
    },
  )
  assert -25 <= boost <= 25
  assert tags


def test_setup_intel_tv_score_boost():
  intel = {"risk": {"consensus_stance": "agree", "risk_adjustment": 0.05}}
  delta, tags = setup_intel_boost(
    setup={"direction": "LONG", "indicators": {"tv_score": 75, "tv_aligned": True}},
    intel=intel,
  )
  assert delta > 0
  assert any("tv" in t for t in tags)


def test_global_risk_adjustment():
  intel = {"risk": {"risk_adjustment": -0.1}}
  assert global_risk_adjustment(intel) == -0.1


def test_setup_intel_global_reject():
  intel = {"risk": {"consensus_stance": "reject"}}
  delta, tags = setup_intel_boost(setup={"direction": "LONG"}, intel=intel)
  assert delta < 0
  assert "global_risk_reject" in tags
