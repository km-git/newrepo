"""Tests for tiered multi-model AI improvement."""

from __future__ import annotations

import pytest

from engine.ai_improvement import (
  ai_improvement_enabled,
  build_improvement_prompt,
  cursor_hosted_models,
  improvement_escalation_routes,
  improvement_workhorse_routes,
  run_multi_model_improvement_review,
  use_all_cursor_models,
)
from engine.llm_model_roster import MODEL


@pytest.fixture(autouse=True)
def _reset_governor_state():
  from engine.model_budget_governor import reset_governor

  reset_governor()
  yield
  reset_governor()


def test_cursor_hosted_models_includes_first_party():
  models = [m["model"] for m in cursor_hosted_models()]
  assert "composer-2.5" in models
  assert "grok-4.5" in models
  assert "cursor-grok-4.5-high" in models


def test_workhorse_routes_use_cursor_hosted():
  routes = improvement_workhorse_routes()
  models = {r[1] for r in routes}
  assert "composer-2.5" in models or "grok-4.5" in models
  assert all(r[2] == "cheap" for r in routes)


def test_escalation_includes_premium_on_hard_disagree(tmp_path, monkeypatch):
  from engine.model_budget_governor import reset_governor

  monkeypatch.setenv("EW_LLM_CACHE_DIR", str(tmp_path))
  monkeypatch.setenv("EW_MODEL_BUDGET_GOVERNOR", "1")
  reset_governor()
  mild = improvement_escalation_routes(stances=["agree", "caution"], metrics_poor=False)
  hard = improvement_escalation_routes(stances=["agree", "reject"], metrics_poor=True)
  hard_models = {r[1] for r in hard}
  assert MODEL["opus"] in hard_models or MODEL["fable"] in hard_models or MODEL["sol"] in hard_models
  assert len(mild) == 0


def test_build_improvement_prompt_compact():
  prompt = build_improvement_prompt(
    metrics={"overall": {"win_rate": 0.55, "decided": 10}, "open_count": 5},
    board={"picks": [{"symbol": "BTC/USDT", "timeframe": "1h", "executive_action": "EXECUTE_NOW"}]},
  )
  assert "TRADING SYSTEM" in prompt
  assert "BTC/USDT" in prompt


def test_run_improvement_skipped_when_disabled(monkeypatch):
  monkeypatch.setenv("EW_AI_IMPROVEMENT", "0")
  result = run_multi_model_improvement_review()
  assert result.get("skipped")


def test_run_improvement_with_mock_panel(monkeypatch, tmp_path):
  from engine.model_budget_governor import reset_governor

  monkeypatch.setenv("EW_AI_IMPROVEMENT", "1")
  monkeypatch.setenv("EW_OKF_BRAIN_DIR", str(tmp_path / "okf"))
  monkeypatch.setenv("EW_USE_ALL_CURSOR_MODELS", "1")
  monkeypatch.setenv("EW_LLM_CACHE_DIR", str(tmp_path / "cache"))
  reset_governor()

  def mock_panel(prompt, verdict, conviction, call_provider, **kwargs):
    return {
      "consensus_stance": "caution",
      "blended_summary": "mock panel",
      "disagreement": False,
      "escalated_to_premium": False,
      "consulted": ["mock"],
    }

  def mock_call(provider, model, tier, task, max_out):
    return {"available": True, "stance": "agree", "summary": f"{model} ok"}

  monkeypatch.setattr("engine.ai_improvement.advisory_credentials_available", lambda: True)
  monkeypatch.setattr("engine.ai_improvement.run_panel", mock_panel)
  monkeypatch.setattr("engine.ai_improvement.make_prompt_call_provider", lambda p: mock_call)

  result = run_multi_model_improvement_review(
    metrics={"overall": {"win_rate": 0.6, "decided": 20}, "open_count": 3},
    use_cache=False,
  )
  assert result.get("consensus_stance") in ("agree", "caution", "reject")
  assert result.get("phase1_workhorse", {}).get("models_count", 0) >= 1
  assert use_all_cursor_models()
