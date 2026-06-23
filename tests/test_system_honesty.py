"""Tests for stop capping and system audit."""

from __future__ import annotations

from core.risk import cap_stop_price, dynamic_stop, MAX_STOP_PCT
from engine.readiness import resolve_execution_status
from engine.system_audit import compute_verdict, run_system_audit


def test_cap_stop_price():
  stop, capped = cap_stop_price("SHORT", 100.0, 500.0, 8.0)
  assert capped is True
  assert abs(stop - 108.0) < 0.01


def test_dynamic_stop_capped():
  r = dynamic_stop("LONG", 100.0, 2.0, -50.0, 200.0, 1.8, max_stop_pct=8.0)
  assert r["capped"] is True
  assert r["distance_pct"] <= 8.01


def test_probe_blocked_on_invalid_impulse():
  status, tier, _ = resolve_execution_status(
    style="scalp",
    direction="LONG",
    wave={"structure": "invalid_impulse (R1)", "impulse_valid": False},
    in_zone=False,
    zone_dist_pct=2.0,
    impulse_valid=False,
    consensus_dir="LONG",
    rr=2.0,
    min_rr=1.2,
    harmonic_near=False,
    indicator={"score": 85, "aligned": True, "threshold": 62, "signals": []},
    executive_verdict="STAGED_GO",
  )
  assert status != "executable" or tier != "probe"


def test_system_audit_fail():
  paper = {"executable_win_rate": 0.38, "executable_closed": 20}
  setups = {
    "oos_avg": 0.48,
    "readiness_ge65_win_rate": 0.35,
    "hedge_ratio": 0.6,
    "caution_ratio": 0.4,
    "full_executable": 0,
    "suspicious_perfect_is": 15,
  }
  v = compute_verdict(paper, setups)
  assert v["status"] == "FAIL"
  assert len(v["failures"]) >= 2


def test_run_system_audit_writes():
  audit = run_system_audit(
    [{"status": "executable", "execution_tier": "probe", "paper_outcome": "loss"}] * 10
    + [{"status": "executable", "execution_tier": "probe", "paper_outcome": "win"}] * 4,
    [{"status": "executable", "readiness_score": 80, "paper_outcome": "loss", "oos_win_rate": "0.4"}],
  )
  assert audit["verdict"]["status"] in ("FAIL", "WARN", "PASS")
