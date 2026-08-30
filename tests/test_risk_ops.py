"""Tests for drawdown circuit breaker."""

from __future__ import annotations

from engine.risk_ops import clear_halt, is_halted, update_equity


def test_halt_latches_on_drawdown(tmp_path, monkeypatch):
  monkeypatch.setenv("EW_RISK_STATE", str(tmp_path / "risk.json"))
  monkeypatch.setenv("EW_DRAWDOWN_HALT_PCT", "10")
  update_equity(10000)
  update_equity(8500)
  assert is_halted() is True


def test_halt_clears_on_drawdown_recovery(tmp_path, monkeypatch):
  monkeypatch.setenv("EW_RISK_STATE", str(tmp_path / "risk.json"))
  monkeypatch.setenv("EW_DRAWDOWN_HALT_PCT", "10")
  update_equity(10000)
  update_equity(8500)
  assert is_halted() is True
  update_equity(10000)
  assert is_halted() is False


def test_emergency_halt_not_auto_cleared(tmp_path, monkeypatch):
  monkeypatch.setenv("EW_RISK_STATE", str(tmp_path / "risk.json"))
  update_equity(10000)
  state = __import__("engine.risk_ops", fromlist=["_load"])._load()
  state["halted"] = True
  state["halt_reason"] = "emergency_flatten"
  __import__("engine.risk_ops", fromlist=["_save"])._save(state)
  update_equity(10000)
  assert is_halted() is True
  clear_halt()
  assert is_halted() is False
