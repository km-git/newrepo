"""Tests for daily trading ops composite tick."""

from __future__ import annotations

from engine.daily_trading_ops import (
  _composite_readiness,
  bootstrap_ops_artifacts,
  run_daily_trading_tick,
  write_daily_ops_report,
)


def test_bootstrap_creates_scheduler(tmp_path, monkeypatch):
  monkeypatch.chdir(tmp_path)
  sched = tmp_path / "output" / "autodream" / "scheduler_state.json"
  result = bootstrap_ops_artifacts()
  assert "scheduler" in result["bootstrapped"]
  assert sched.exists()


def test_composite_readiness_deploy_go():
  r = _composite_readiness(
    proof={"verdict": "PROOF_GO"},
    goat={"composite_verdict": "GO"},
    tactical={"posture": "NEUTRAL"},
    health={"healthy": True},
  )
  assert r["verdict"] == "DEPLOY_GO"
  assert r["blockers"] == []


def test_composite_readiness_hold_on_halt(monkeypatch):
  monkeypatch.setattr("engine.risk_ops.is_halted", lambda: True)
  r = _composite_readiness(
    proof={"verdict": "PROOF_GO"},
    goat={"composite_verdict": "GO"},
    tactical={"posture": "NEUTRAL"},
    health={"healthy": True},
  )
  assert r["verdict"] == "DEPLOY_HOLD"
  assert "risk_halted" in r["blockers"]


def test_composite_readiness_hold_defensive():
  r = _composite_readiness(
    proof={"verdict": "PROOF_PENDING"},
    goat={"composite_verdict": "CONDITIONAL"},
    tactical={"posture": "DEFENSIVE"},
    health={"healthy": False},
  )
  assert r["verdict"] in ("DEPLOY_HOLD", "DEPLOY_CONDITIONAL")
  assert "tactical_defensive" in r["blockers"] or "paper_proof_PROOF_PENDING" in r["blockers"]


def test_run_daily_tick_offline(tmp_path, monkeypatch):
  monkeypatch.chdir(tmp_path)
  monkeypatch.setenv("EW_DAILY_OPS_REPORT", str(tmp_path / "report.md"))
  monkeypatch.setenv("EW_DAILY_OPS_STATE", str(tmp_path / "state.json"))
  monkeypatch.setenv("EW_RISK_STATE", str(tmp_path / "risk.json"))
  monkeypatch.setenv("EW_PORTFOLIO_STATE", str(tmp_path / "portfolio.json"))
  monkeypatch.setenv("EW_PAPER_FORWARD_LEDGER", str(tmp_path / "ledger.jsonl"))
  monkeypatch.setenv("EW_PAPER_FORWARD_STATE", str(tmp_path / "pf_state.json"))
  monkeypatch.setenv("EW_PAPER_FORWARD_REPORT", str(tmp_path / "pf_report.md"))
  monkeypatch.setenv("EW_HEALTH_REQUIRE_ARTIFACTS", "0")
  monkeypatch.setenv("EW_PORTFOLIO_RISK", "0")
  monkeypatch.setenv("EW_TACTICAL_SAFEGUARD", "0")

  def fake_paper(**kwargs):
    return {"ok": True, "proof": {"verdict": "PROOF_PENDING", "metrics": {"days": 1}}}

  def fake_goat(**kwargs):
    return {"composite_verdict": "INSUFFICIENT_DATA"}

  monkeypatch.setattr("engine.paper_forward_tracker.run_paper_forward_tick", fake_paper)
  monkeypatch.setattr("engine.effectiveness_audit.run_full_effectiveness_audit", fake_goat)

  tick = run_daily_trading_tick(fetch_ohlc=False, bootstrap=True)
  assert "readiness" in tick
  assert tick["readiness"]["verdict"] in ("DEPLOY_HOLD", "DEPLOY_CONDITIONAL")
  assert (tmp_path / "report.md").exists()


def test_write_report(tmp_path):
  tick = {
    "timestamp_utc": "2026-01-01T00:00:00+00:00",
    "readiness": {
      "verdict": "DEPLOY_CONDITIONAL",
      "proof_verdict": "PROOF_PENDING",
      "goat_verdict": "INSUFFICIENT_DATA",
      "tactical_posture": "CAUTIOUS",
      "healthy": True,
      "halted": False,
      "blockers": ["paper_proof_PROOF_PENDING"],
    },
  }
  path = tmp_path / "ops.md"
  text = write_daily_ops_report(tick, path=path)
  assert "Daily Trading Ops" in text
  assert path.exists()
