"""E2E pipeline and continuous improvement tests."""

from __future__ import annotations

import json
from pathlib import Path

import pytest

from engine.e2e_pipeline import e2e_enabled, e2e_status, run_e2e_cycle
from engine.improvement_cycle import improvement_enabled, improvement_report, run_improvement_cycle
from engine.system_health import run_health_checks, save_health


@pytest.fixture
def isolated_paths(tmp_path, monkeypatch):
  monkeypatch.setenv("EW_OKF_BRAIN_DIR", str(tmp_path / "okf"))
  monkeypatch.setenv("EW_PAPER_LEDGER", str(tmp_path / "paper.json"))
  monkeypatch.setenv("EW_HEALTH_PATH", str(tmp_path / "health.json"))
  monkeypatch.setenv("EW_E2E_STATE", str(tmp_path / "e2e.json"))
  monkeypatch.setenv("EW_IMPROVEMENT_LOG", str(tmp_path / "cycles.jsonl"))
  monkeypatch.setenv("EW_WEB_INTEL", "0")
  monkeypatch.setenv("EW_WS_ENABLED", "0")
  # Empty tracker — avoid live fetch during resolve
  import engine.outcome_tracker as ot
  monkeypatch.setattr(ot, "TRACKED_PATH", tmp_path / "tracked_setups.json")
  monkeypatch.setattr(ot, "METRICS_PATH", tmp_path / "metrics.json")
  monkeypatch.setattr(ot, "PERFORMANCE_MD", tmp_path / "HISTORICAL_PERFORMANCE.md")
  (tmp_path / "tracked_setups.json").write_text('{"open":[],"closed":[]}')
  return tmp_path


def test_improvement_cycle_offline(isolated_paths):
  result = run_improvement_cycle(is_crypto=False)
  assert "metrics" in result
  assert "health" in result
  assert result["cycle"]["timestamp_utc"]


def test_improvement_report(isolated_paths):
  run_improvement_cycle(is_crypto=False)
  report = improvement_report()
  assert report["enabled"] is True
  assert "recent_cycles" in report


def test_health_checks(isolated_paths):
  health = run_health_checks()
  assert health["total"] >= 5
  path = save_health(health)
  assert Path(path).exists()


def test_e2e_cycle_monitor_only(isolated_paths, monkeypatch):
  monkeypatch.setenv("EW_IMPROVEMENT_CYCLE", "1")
  result = run_e2e_cycle(
    batch_n=0,
    skip_batch=True,
    skip_monitor=True,
    execute=False,
  )
  assert result["ok"] is True
  assert "phases" in result
  assert "learn" in result["phases"]


def test_e2e_status(isolated_paths):
  status = e2e_status()
  assert status["enabled"] == e2e_enabled()
  assert "improvement" in status


def test_improvement_disabled(monkeypatch):
  monkeypatch.setenv("EW_IMPROVEMENT_CYCLE", "0")
  assert improvement_enabled() is False
  result = run_improvement_cycle()
  assert result.get("skipped") is True
