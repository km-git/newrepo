"""Goal-mode orchestration and autoresearch (Swarm Trader pattern)."""

from __future__ import annotations

import json

import pytest

from engine.autoresearch import (
  autoresearch_enabled,
  latest_experiments_summary,
  propose_experiments,
  run_autoresearch_batch,
)
from engine.goal_mode import (
  auto_deploy_allowed,
  goal_mode_enabled,
  run_goal_mode_cycle,
  swarm_agent_map,
)


def test_swarm_agent_map_keys():
  m = swarm_agent_map()
  assert "risk_manager" in m
  assert "autoresearch" in m
  assert len(m) >= 10


def test_goal_mode_enabled_env(monkeypatch):
  monkeypatch.delenv("EW_GOAL_MODE", raising=False)
  assert goal_mode_enabled() is False
  monkeypatch.setenv("EW_GOAL_MODE", "1")
  assert goal_mode_enabled() is True


def test_auto_deploy_paper_default(monkeypatch):
  monkeypatch.delenv("EW_GOAL_MODE_AUTO_PAPER", raising=False)
  assert auto_deploy_allowed() is True
  monkeypatch.setenv("EW_GOAL_MODE_AUTO_PAPER", "0")
  assert auto_deploy_allowed() is False


def test_autoresearch_batch(tmp_path, monkeypatch):
  log = tmp_path / "experiments.jsonl"
  import engine.autoresearch as ar

  monkeypatch.setattr(ar, "EXPERIMENT_LOG", log)
  out = run_autoresearch_batch(max_experiments=2, record_baseline=True)
  assert out["baseline_fitness"] is not None
  assert len(out["proposals"]) == 2
  assert log.exists()
  summary = latest_experiments_summary()
  assert summary["count"] >= 3


def test_propose_experiments():
  props = propose_experiments()
  assert any(p["id"] == "llm_execution_panel" for p in props)


def test_run_goal_mode_cycle_mocked(monkeypatch):
  monkeypatch.setenv("EW_GOAL_MODE_AUTO_PAPER", "0")
  monkeypatch.setenv("EW_GOAL_MODE_AUTORESEARCH", "0")

  def fake_e2e(**kwargs):
    return {
      "ok": True,
      "healthy": True,
      "phases": {"learn": {"resolved": 0}, "record": {"rows": 0}},
    }

  import engine.e2e_pipeline as ep

  monkeypatch.setattr(ep, "run_e2e_cycle", fake_e2e)

  result = run_goal_mode_cycle(batch_n=0, execute_paper=False, skip_batch=True, skip_monitor=True)
  assert result["ok"] is True
  assert result["phases"]["backtest"]["fitness"] is not None
  assert result["phases"]["validate"]["human_gate"]["paper_auto"] is False
  assert "research" in result["phases"]
