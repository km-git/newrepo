"""Tests for LLM cost estimation."""

from __future__ import annotations

from engine.llm_cost import (
  advisory_scenario_comparison,
  attach_cost_estimate,
  estimate_call_cost,
  task_tier,
)


def test_cheap_cheaper_than_premium():
  cheap = estimate_call_cost("gpt-4o-mini", 450, 180)
  prem = estimate_call_cost("gpt-4o", 450, 180)
  assert cheap < prem


def test_task_tier_screen_is_cheap():
  assert task_tier("screen") == "cheap"
  assert task_tier("tiebreaker") == "standard"
  assert task_tier("architect") == "standard"


def test_scenario_comparison_ensemble_cheaper_than_dual_premium():
  comp = advisory_scenario_comparison()
  by_id = {s["id"]: s for s in comp["scenarios"]}
  assert by_id["ensemble_blended"]["est_cost_usd"] < by_id["dual_premium"]["est_cost_usd"]
  assert comp["savings_pct_vs_dual_premium"] > 50


def test_attach_cost_estimate():
  budget = {"est_input_tokens": 450, "max_output_tokens": 280}
  routes = [("openai", "gpt-4o-mini", "cheap")]
  out = attach_cost_estimate(budget, routes)
  assert "cost_estimate" in out
  assert out["cost_estimate"]["est_total_usd"] > 0
  assert "scenario_comparison" in out
