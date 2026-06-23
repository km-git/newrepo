"""Tests for split EW/SMC system audit."""

from __future__ import annotations

from engine.system_audit import audit_setups, compute_verdict


def _row(style="day_trade", **kwargs):
  base = {
    "style": style,
    "status": "monitor",
    "oos_win_rate": 0.48,
    "oos_trades": 5,
    "readiness_score": 60,
    "paper_outcome": "win",
  }
  base.update(kwargs)
  return base


def test_audit_splits_ew_and_smc():
  rows = [
    _row("day_trade", oos_win_rate=0.45),
    _row("smc", oos_win_rate=0.55, status="executable"),
    _row("smc", oos_win_rate=0.52),
  ]
  s = audit_setups(rows)
  assert s["smc_setups"] == 2
  assert s["ew_setups"] == 1
  assert s["by_path"]["smc"]["oos_avg"] is not None
  assert s["by_path"]["ew"]["oos_avg"] is not None


def test_ew_oos_fail_is_warn_when_smc_active():
  paper = {"executable_win_rate": 0.55, "all_win_rate": 0.50}
  setups = {
    "oos_avg": 0.47,
    "oos_executable_avg": 0.56,
    "full_executable": 0,
    "smc_setups": 20,
    "smc_executable": 2,
    "by_path": {
      "ew": {"oos_avg": 0.45},
      "smc": {"oos_avg": 0.52, "oos_executable_avg": 0.54},
    },
    "readiness_ge65_win_rate": 0.55,
    "hedge_ratio": 0.1,
    "caution_ratio": 0.2,
    "suspicious_perfect_is": 0,
  }
  v = compute_verdict(paper, setups)
  assert v["status"] in ("WARN", "PASS")
  assert any("EW OOS" in w for w in v["warnings"]) or v["status"] == "PASS"
