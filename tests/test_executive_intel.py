"""Tests for executive intel layer."""

from __future__ import annotations

from engine.executive_intel import executive_intel_enabled, setup_intel_boost


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
