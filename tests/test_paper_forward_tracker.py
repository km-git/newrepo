"""Tests for paper forward proof tracker (LLM-free)."""

from __future__ import annotations

import json

from engine.paper_forward_tracker import (
  backfill_paper_forward_window,
  evaluate_proof_verdict,
  record_snapshot,
  rolling_metrics,
  run_paper_forward_tick,
  write_forward_report,
)


def _paper_summary(pnl: float, wins: int = 2, losses: int = 1) -> dict:
  return {
    "ok": True,
    "starting_equity_usd": 50000,
    "ending_equity_usd": 50000 + pnl,
    "realized_pnl_usd": pnl,
    "return_pct": pnl / 50000 * 100,
    "wins": wins,
    "losses": losses,
    "simulated": wins + losses,
    "candidates": 5,
    "fees_usd": 10,
  }


def test_record_and_rolling_metrics(tmp_path, monkeypatch):
  monkeypatch.setenv("EW_PAPER_FORWARD_LEDGER", str(tmp_path / "ledger.jsonl"))
  record_snapshot(_paper_summary(100))
  record_snapshot(_paper_summary(50))
  m = rolling_metrics(window_days=30)
  assert m["days"] == 1  # same UTC day replaces
  assert m["cumulative_pnl_usd"] == 50


def test_proof_verdict_pending(monkeypatch):
  metrics = {"days": 2, "cumulative_pnl_usd": 500, "win_rate": 0.6}
  proof = evaluate_proof_verdict(metrics)
  assert proof["verdict"] == "PROOF_PENDING"


def test_proof_verdict_go(monkeypatch):
  monkeypatch.setenv("EW_PAPER_PROOF_MIN_DAYS", "3")
  metrics = {"days": 10, "cumulative_pnl_usd": 1200, "win_rate": 0.55}
  proof = evaluate_proof_verdict(metrics)
  assert proof["verdict"] == "PROOF_GO"


def test_proof_verdict_no_go(monkeypatch):
  monkeypatch.setenv("EW_PAPER_PROOF_MIN_DAYS", "3")
  metrics = {"days": 10, "cumulative_pnl_usd": -500, "win_rate": 0.4}
  proof = evaluate_proof_verdict(metrics)
  assert proof["verdict"] == "PROOF_NO_GO"


def test_write_report(tmp_path, monkeypatch):
  monkeypatch.setenv("EW_PAPER_FORWARD_REPORT", str(tmp_path / "report.md"))
  text = write_forward_report(
    proof={"verdict": "PROOF_PENDING", "gates": [], "metrics": {"days": 1, "window_days": 30}},
  )
  assert "Paper Forward Proof" in text
  assert (tmp_path / "report.md").exists()


def test_run_tick_offline(tmp_path, monkeypatch):
  monkeypatch.setenv("EW_PAPER_FORWARD_LEDGER", str(tmp_path / "ledger.jsonl"))
  monkeypatch.setenv("EW_PAPER_FORWARD_STATE", str(tmp_path / "state.json"))
  monkeypatch.setenv("EW_PAPER_FORWARD_REPORT", str(tmp_path / "report.md"))

  def fake_learning(**kwargs):
    return {"overall": {"win_rate": 0.62, "decided": 100}}

  def fake_paper(**kwargs):
    return _paper_summary(250, wins=3, losses=1)

  def fake_audit(**kwargs):
    return {"composite_verdict": "GO"}

  monkeypatch.setattr("engine.outcome_tracker.run_learning_phase", fake_learning)
  monkeypatch.setattr("engine.paper_simulator.run_paper_simulation", fake_paper)
  monkeypatch.setattr("engine.effectiveness_audit.run_full_effectiveness_audit", fake_audit)

  monkeypatch.setenv("EW_RISK_STATE", str(tmp_path / "risk.json"))

  result = run_paper_forward_tick(fetch_ohlc=False)
  assert result["ok"] is True
  assert result["proof"]["verdict"] in ("PROOF_PENDING", "PROOF_GO")
  assert (tmp_path / "ledger.jsonl").exists()
  risk = result["phases"].get("risk_ops") or {}
  assert risk.get("equity_usd") == 50250
  assert (tmp_path / "risk.json").exists()


def test_backfill_records_missing_days(tmp_path, monkeypatch):
  monkeypatch.setenv("EW_PAPER_FORWARD_LEDGER", str(tmp_path / "ledger.jsonl"))
  monkeypatch.setenv("EW_PAPER_FORWARD_STATE", str(tmp_path / "state.json"))
  monkeypatch.setenv("EW_PAPER_FORWARD_REPORT", str(tmp_path / "report.md"))
  monkeypatch.setenv("EW_PAPER_PROOF_DAYS", "3")
  monkeypatch.setenv("EW_PAPER_FORWARD_SKIP_RESOLVE", "1")

  calls: list[str] = []

  def fake_paper(**kwargs):
    calls.append(kwargs.get("as_of") or "live")
    pnl = 10.0 if len(calls) == 1 else -5.0
    return _paper_summary(pnl, wins=1 if pnl > 0 else 0, losses=0 if pnl > 0 else 1)

  monkeypatch.setattr("engine.paper_simulator.run_paper_simulation", fake_paper)

  result = backfill_paper_forward_window(days=3, fetch_ohlc=False, force=True)
  assert result["dates_backfilled"] == 3
  assert len(calls) == 3
  metrics = rolling_metrics(window_days=3)
  assert metrics["days"] == 3
  assert metrics["cumulative_pnl_usd"] == 0.0
  proof = evaluate_proof_verdict(metrics)
  assert proof["verdict"] in ("PROOF_PENDING", "PROOF_NO_GO", "PROOF_GO")
