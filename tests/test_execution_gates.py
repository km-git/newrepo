"""Tests for unified execution gate bundle."""

from __future__ import annotations

from engine.calibrated_execution import gates_passed, validate_execution_gates
from engine.executive_board import _executive_action


def _smc_setup(**kwargs):
  base = {
    "style": "smc",
    "status": "executable",
    "execution_tier": "full",
    "oos_gate": "passed",
    "oos_win_rate": 0.62,
    "oos_trades": 20,
    "entry_confirm_ok": True,
    "structure_blocked": False,
    "vp_filter_ok": True,
    "msb_gate": None,
  }
  base.update(kwargs)
  return base


def test_validate_execution_gates_passes_smc():
  ok, out, reason = validate_execution_gates(_smc_setup())
  assert ok is True
  assert out.get("gates_passed") is True
  assert reason == "all gates passed"


def test_validate_blocks_counter_trend_structure():
  ok, out, reason = validate_execution_gates(_smc_setup(structure_blocked=True))
  assert ok is False
  assert out["status"] == "monitor"
  assert "structure" in reason


def test_validate_blocks_missing_confirm():
  ok, _, reason = validate_execution_gates(_smc_setup(entry_confirm_ok=False))
  assert ok is False
  assert "confirm" in reason


def test_executive_no_execute_now_without_gates():
  setup = _smc_setup(status="monitor", oos_gate=None)
  action, size, _ = _executive_action(setup, exec_score=90, blocker="none")
  assert action != "EXECUTE_NOW"
  assert size <= 50


def test_executive_execute_now_when_all_gates():
  action, size, playbook = _executive_action(_smc_setup(), exec_score=90, blocker="none")
  assert action == "EXECUTE_NOW"
  assert size == 100
  assert "All gates passed" in playbook


def test_gates_passed_helper():
  assert gates_passed(_smc_setup()) is True
  assert gates_passed(_smc_setup(oos_trades=2, oos_win_rate=0.9)) is False
