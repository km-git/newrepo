"""Tests for resource gap audit — self-challenge missing tools and data."""

from __future__ import annotations

from engine.resource_gap_audit import (
  audit_resources,
  gap_audit_enabled,
  gap_audit_summary,
  run_resource_gap_audit,
)


def test_gap_audit_enabled_default():
  assert gap_audit_enabled() is True


def test_audit_resources_structure():
  report = audit_resources(include_runtime=False)
  assert "summary" in report
  assert "top_gaps" in report
  assert "challenge_questions" in report
  assert report["summary"]["total_watchlist"] >= 20
  assert len(report["challenge_questions"]) >= 5


def test_top_gaps_sorted_by_impact():
  report = audit_resources(include_runtime=False)
  gaps = report.get("top_gaps") or []
  if len(gaps) >= 2:
    ranks = {"critical": 0, "high": 1, "medium": 2, "low": 3}
    assert ranks.get(gaps[0].get("impact", "low"), 9) <= ranks.get(gaps[1].get("impact", "low"), 9)


def test_run_gap_audit_persists(tmp_path, monkeypatch):
  import engine.resource_gap_audit as rga

  out = tmp_path / "gap.json"
  monkeypatch.setattr(rga, "AUDIT_PATH", out)
  monkeypatch.setenv("EW_OKF_BRAIN_DIR", str(tmp_path / "okf"))
  result = rga.run_resource_gap_audit(persist=True, persist_okf=False)
  assert not result.get("skipped")
  assert out.exists()


def test_gap_audit_summary_from_report():
  report = audit_resources(include_runtime=False)
  summary = gap_audit_summary()
  assert "gaps" in summary or summary.get("gaps") is not None
