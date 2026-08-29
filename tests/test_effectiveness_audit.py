"""Integration tests for effectiveness audit."""

from __future__ import annotations

from engine.effectiveness_audit import run_full_effectiveness_audit, write_effectiveness_report


def test_full_audit_offline(tmp_path, monkeypatch):
  monkeypatch.chdir(tmp_path)
  monkeypatch.setenv("EW_EFFECTIVENESS_REPORT", str(tmp_path / "EFFECTIVENESS.md"))
  monkeypatch.setenv("EW_EFFECTIVENESS_JSON", str(tmp_path / "audit.json"))

  # Minimal tracked state for walk-forward
  tracked = tmp_path / "output" / "autodream"
  tracked.mkdir(parents=True)
  closed = []
  for i in range(30):
    closed.append({
      "symbol": "BTC/USDT",
      "timeframe": "15m" if i % 2 == 0 else "1d",
      "direction": "LONG",
      "status": "tp1_hit" if i % 3 != 0 else "sl_hit",
      "wae": 100000,
      "stop_loss": 95000,
      "tp1": 105000,
      "closed_at": f"2024-06-{i+1:02d}T12:00:00+00:00",
    })
  import json
  (tracked / "tracked_setups.json").write_text(json.dumps({"open": [], "closed": closed}))

  result = run_full_effectiveness_audit(fetch_ohlc=False, include_walk_forward=True)
  assert "composite_verdict" in result
  assert "walk_forward" in result
  assert "outcomes" in result
  assert "recommendations" in result
  assert (tmp_path / "audit.json").exists()



def test_paper_failure_forces_no_go(monkeypatch):
  monkeypatch.setenv("EW_EFFECTIVENESS_PAPER", "1")

  def fake_paper(**kwargs):
    return {"ok": False, "reason": "backtest_failed"}

  def fake_outcomes():
    return {
      "ok": True,
      "gate": {"verdict": "GO"},
      "regime": {"regime_gate_passed": True},
    }

  def fake_wf(**kwargs):
    return {
      "ok": True,
      "deployment_gate": {"verdict": "GO"},
      "stitched_oos": {"n": 300},
      "n_folds": 5,
      "n_closed": 300,
    }

  monkeypatch.setattr("engine.effectiveness_audit.run_paper_gate_audit", fake_paper)
  monkeypatch.setattr("engine.effectiveness_audit.run_outcome_gate_audit", fake_outcomes)
  monkeypatch.setattr("engine.effectiveness_audit.run_walk_forward_validation", fake_wf)

  result = run_full_effectiveness_audit(fetch_ohlc=False, include_walk_forward=True)
  assert result["composite_verdict"] == "NO_GO"


def test_write_report(tmp_path):
  audit = {
    "audited_at": "2026-01-01T00:00:00+00:00",
    "composite_verdict": "INSUFFICIENT_DATA",
    "walk_forward": {
      "ok": True,
      "n_folds": 3,
      "n_closed": 100,
      "stitched_oos": {"n": 50, "sharpe": 0.8},
      "deployment_gate": {
        "verdict": "INSUFFICIENT_DATA",
        "gates": [{"gate": "min_trades", "passed": False, "detail": "n=50"}],
      },
    },
    "recommendations": ["Continue paper trading"],
  }
  path = tmp_path / "report.md"
  text = write_effectiveness_report(audit, path=path)
  assert "Effectiveness Audit" in text
  assert path.exists()
