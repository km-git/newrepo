"""Tests for tactical safeguard — adaptive account protection."""

from __future__ import annotations

import json

from core.risk import DCA_PROFILE_30_70, DCA_PROFILE_PYRAMID
from engine.tactical_safeguard import (
  POSTURE_CAUTIOUS,
  POSTURE_DEFENSIVE,
  POSTURE_NEUTRAL,
  POSTURE_OPPORTUNISTIC,
  adjust_dca_for_posture,
  apply_tactical_to_row,
  assess_tactical_posture,
  gate_tactical,
  tactical_risk_multiplier,
  tactical_safeguard_enabled,
)


def test_tactical_safeguard_default_on():
  assert tactical_safeguard_enabled() is True


def test_assess_neutral_when_disabled(monkeypatch):
  monkeypatch.setenv("EW_TACTICAL_SAFEGUARD", "0")
  posture = assess_tactical_posture()
  assert posture["posture"] == POSTURE_NEUTRAL
  assert posture["risk_mult"] == 1.0


def test_assess_defensive_on_halt(tmp_path, monkeypatch):
  monkeypatch.setenv("EW_RISK_STATE", str(tmp_path / "risk.json"))
  monkeypatch.setenv("EW_DRAWDOWN_HALT_PCT", "10")
  state = {
    "peak_equity_usd": 50000,
    "current_equity_usd": 44000,
    "drawdown_pct": 12.0,
    "halted": True,
    "halt_reason": "drawdown",
  }
  (tmp_path / "risk.json").write_text(json.dumps(state), encoding="utf-8")

  posture = assess_tactical_posture()
  assert posture["posture"] == POSTURE_DEFENSIVE
  assert posture["halted"] is True
  assert posture["probe_only"] is True
  assert posture["risk_mult"] == 0.50


def test_assess_neutral_on_proof_go_below_opportunistic_threshold(tmp_path, monkeypatch):
  """Proof GO boosts score but OPPORTUNISTIC needs score >= 62."""
  monkeypatch.setenv("EW_RISK_STATE", str(tmp_path / "risk.json"))
  monkeypatch.setenv("EW_PORTFOLIO_STATE", str(tmp_path / "portfolio_state.json"))
  monkeypatch.setenv("EW_PORTFOLIO_RISK", "0")
  monkeypatch.setenv("EW_PAPER_FORWARD_LEDGER", str(tmp_path / "ledger.jsonl"))
  monkeypatch.setenv("EW_PAPER_PROOF_MIN_DAYS", "3")
  (tmp_path / "risk.json").write_text(
    json.dumps({"peak_equity_usd": 50000, "drawdown_pct": 0, "halted": False}),
    encoding="utf-8",
  )
  ledger = [
    {"date": "2026-08-25", "realized_pnl_usd": 200, "wins": 2, "losses": 0},
    {"date": "2026-08-26", "realized_pnl_usd": 150, "wins": 2, "losses": 0},
    {"date": "2026-08-27", "realized_pnl_usd": 100, "wins": 1, "losses": 0},
    {"date": "2026-08-28", "realized_pnl_usd": 50, "wins": 1, "losses": 0},
  ]
  (tmp_path / "ledger.jsonl").write_text(
    "\n".join(json.dumps(r) for r in ledger) + "\n",
    encoding="utf-8",
  )

  posture = assess_tactical_posture()
  assert posture["proof_verdict"] == "PROOF_GO"
  assert posture["posture"] == POSTURE_NEUTRAL
  assert posture["score"] >= 55


def test_tactical_risk_multiplier_opportunistic():
  posture = {"posture": POSTURE_OPPORTUNISTIC, "risk_mult": 1.05}
  mult, factors = tactical_risk_multiplier(posture)
  assert mult == 1.05
  assert any("OPPORTUNISTIC" in f for f in factors)
  posture = {"posture": POSTURE_DEFENSIVE, "risk_mult": 0.50}
  mult, factors = tactical_risk_multiplier(posture)
  assert mult == 0.50
  assert any("DEFENSIVE" in f for f in factors)


def test_adjust_dca_defensive_prefers_30_70():
  posture = {"posture": POSTURE_CAUTIOUS}
  result = {
    "step9_market_confluence": {"btc_correlation": {"correlation": 0.78}},
  }
  profile, reason = adjust_dca_for_posture(
    DCA_PROFILE_PYRAMID,
    "default pyramid",
    symbol="ADA/USDT",
    tf="1d",
    result=result,
    posture=posture,
  )
  assert profile == DCA_PROFILE_30_70
  assert "30/70" in reason or "defensive" in reason.lower()


def test_apply_tactical_caps_size_and_risk():
  posture = {
    "posture": POSTURE_CAUTIOUS,
    "score": 35,
    "factors": ["drawdown_elevated"],
    "size_cap_pct": 60.0,
    "max_account_risk_pct": 0.55,
    "probe_only": False,
  }
  row = apply_tactical_to_row(
    {
      "gtc_size_cap_pct": 100,
      "account_risk_pct": 0.9,
      "honest_execution_tier": "full",
    },
    posture=posture,
  )
  assert row["gtc_size_cap_pct"] == 60.0
  assert row["account_risk_pct"] == 0.55
  assert row["tactical_posture"] == POSTURE_CAUTIOUS


def test_apply_tactical_downgrades_full_to_probe():
  posture = {
    "posture": POSTURE_DEFENSIVE,
    "score": 20,
    "factors": ["risk_halted"],
    "size_cap_pct": 35.0,
    "max_account_risk_pct": 0.35,
    "probe_only": True,
  }
  row = apply_tactical_to_row(
    {"honest_execution_tier": "full", "gtc_size_cap_pct": 100},
    posture=posture,
  )
  assert row["honest_execution_tier"] == "probe"
  assert "tactical_downgrade" in row


def test_gate_blocks_halted_account():
  posture = {"halted": True, "posture": POSTURE_DEFENSIVE}
  ok, reasons = gate_tactical({"honest_execution_tier": "probe"}, posture=posture)
  assert ok is False
  assert "tactical_risk_halted" in reasons


def test_gate_blocks_full_size_in_defensive():
  posture = {
    "halted": False,
    "posture": POSTURE_DEFENSIVE,
    "max_account_risk_pct": 0.35,
  }
  ok, reasons = gate_tactical(
    {"honest_execution_tier": "full", "account_risk_pct": 0.5},
    posture=posture,
  )
  assert ok is False
  assert "tactical_defensive_no_full_size" in reasons


def test_gate_allows_probe_in_defensive():
  posture = {
    "halted": False,
    "posture": POSTURE_DEFENSIVE,
    "max_account_risk_pct": 0.35,
  }
  ok, reasons = gate_tactical(
    {"honest_execution_tier": "probe", "account_risk_pct": 0.3},
    posture=posture,
  )
  assert ok is True
  assert reasons == []
