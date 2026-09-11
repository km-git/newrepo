"""Tests for autonomous ops and deep research."""

from __future__ import annotations

import json
from pathlib import Path

from engine.autonomous_ops import autonomous_enabled, run_autonomous_tick
from engine.autoresearch import auto_promote_best_experiment, auto_promote_enabled
from engine.deep_research import deep_research_enabled, gather_market_intel


def test_autonomous_enabled_default():
  assert autonomous_enabled()


def test_deep_research_enabled_default():
  assert deep_research_enabled()


def test_gather_market_intel_offline(monkeypatch):
  monkeypatch.setenv("EW_WEB_INTEL", "0")
  monkeypatch.setenv("EW_SOCIAL_INTEL", "0")
  intel = gather_market_intel(["BTC/USDT"])
  assert "symbols" in intel


def test_autonomous_tick_offline(monkeypatch, tmp_path):
  monkeypatch.setenv("EW_AUTONOMOUS_OPS", "1")
  monkeypatch.setenv("EW_PR_AUTO_MERGE", "0")
  monkeypatch.setenv("EW_DEEP_RESEARCH", "0")
  monkeypatch.setenv("EW_OKF_BRAIN_DIR", str(tmp_path / "okf"))
  monkeypatch.setenv("EW_AUTONOMOUS_TICK_LOG", str(tmp_path / "ticks.jsonl"))
  monkeypatch.setenv("EW_AUTONOMOUS_STATE", str(tmp_path / "state.json"))
  monkeypatch.setenv("EW_IMPROVEMENT_CYCLE", "1")
  monkeypatch.setenv("EW_IMPROVEMENT_LLM", "0")
  monkeypatch.setenv("EW_AUTORESEARCH", "0")

  tick = run_autonomous_tick(skip_pr=True, skip_research=True, skip_autoresearch=True)
  assert "phases" in tick
  assert "learning" in tick["phases"]


def test_auto_promote_skipped_when_disabled(monkeypatch):
  monkeypatch.setenv("EW_AUTORESEARCH_AUTO_PROMOTE", "0")
  assert not auto_promote_enabled()
  result = auto_promote_best_experiment({"ok": True, "best": {"experiment_id": "x", "fitness": 0.9}})
  assert result.get("skipped")


def test_auto_promote_when_fitness_improves(monkeypatch, tmp_path):
  monkeypatch.setenv("EW_AUTORESEARCH_AUTO_PROMOTE", "1")
  monkeypatch.setenv("EW_AUTORESEARCH_ACTIVE_ENV", str(tmp_path / "active_env.json"))
  monkeypatch.setenv("EW_AUTORESEARCH_PROMOTE_DELTA", "0.01")
  monkeypatch.setenv("EW_AUTORESEARCH_MIN_FITNESS", "0.3")
  monkeypatch.setenv("EW_OKF_BRAIN_DIR", str(tmp_path / "okf"))
  monkeypatch.setenv("EW_AUTORESEARCH_LOG", str(tmp_path / "experiments.jsonl"))

  eval_result = {
    "ok": True,
    "evaluated": [
      {"experiment_id": "baseline_eval", "fitness": {"fitness": 0.4}},
      {"experiment_id": "dynamic_risk_on", "fitness": {"fitness": 0.5}},
    ],
    "best": {"experiment_id": "dynamic_risk_on", "fitness": 0.5},
  }
  result = auto_promote_best_experiment(eval_result)
  assert result.get("promoted") is True
  env_path = Path(result["env_path"])
  assert env_path.exists()
  doc = json.loads(env_path.read_text())
  assert doc["experiment_id"] == "dynamic_risk_on"
