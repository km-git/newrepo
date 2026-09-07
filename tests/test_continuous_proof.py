"""Tests for continuous proof cycle."""

from __future__ import annotations

from engine.continuous_proof import run_continuous_proof_cycle, write_continuous_report


def test_continuous_cycle_offline(tmp_path, monkeypatch):
  monkeypatch.setenv("EW_CONTINUOUS_PROOF_REPORT", str(tmp_path / "report.md"))
  monkeypatch.setenv("EW_CONTINUOUS_PROOF_LOG", str(tmp_path / "cycle.jsonl"))
  monkeypatch.setenv("EW_PAPER_FORWARD_LEDGER", str(tmp_path / "ledger.jsonl"))
  monkeypatch.setenv("EW_PAPER_FORWARD_STATE", str(tmp_path / "state.json"))
  monkeypatch.setenv("EW_PAPER_FORWARD_REPORT", str(tmp_path / "forward.md"))
  monkeypatch.setenv("EW_PAPER_TRADES_LOG", str(tmp_path / "trades.jsonl"))
  monkeypatch.setenv("EW_PAPER_LEARNED_POLICY", str(tmp_path / "policy.json"))
  monkeypatch.setenv("EW_PAPER_POLICY_REPORT", str(tmp_path / "policy.md"))
  monkeypatch.setenv("EW_PAPER_FORWARD_SKIP_RESOLVE", "1")
  monkeypatch.setenv("EW_TACTICAL_SAFEGUARD", "0")

  def fake_learning(**kwargs):
    return {"overall": {"win_rate": 0.52, "decided": 200}}

  def fake_paper(**kwargs):
    return {
      "ok": True,
      "starting_equity_usd": 50000,
      "ending_equity_usd": 50100,
      "realized_pnl_usd": 100,
      "wins": 2,
      "losses": 1,
      "simulated": 3,
      "candidates": 10,
      "fees_usd": 5,
      "trades": [],
    }

  def fake_forward(**kwargs):
    from engine.paper_forward_tracker import record_snapshot, evaluate_proof_verdict, write_forward_report

    snap = record_snapshot(fake_paper(), tracked_metrics={"overall": {"win_rate": 0.52, "decided": 200}})
    proof = evaluate_proof_verdict()
    write_forward_report(latest_snapshot=snap, proof=proof)
    return {"ok": True, "proof": proof, "snapshot": snap, "phases": {"paper": fake_paper()}}

  monkeypatch.setattr("engine.outcome_tracker.run_learning_phase", fake_learning)
  monkeypatch.setattr("engine.paper_forward_tracker.run_paper_forward_tick", fake_forward)

  result = run_continuous_proof_cycle(fetch_ohlc=False)
  assert result["ok"] is True
  assert (tmp_path / "report.md").exists()


def test_write_report():
  text = write_continuous_report({
    "timestamp_utc": "2026-01-01",
    "summary": {"verdict": "PROOF_PENDING", "cumulative_pnl_usd": 0},
    "proof": {"gates": []},
    "phases": {},
  })
  assert "Continuous Proof Cycle" in text
