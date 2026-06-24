"""Tests for live loop helpers."""

from __future__ import annotations

from engine.execution_queue import collect_monitor_upgrades_from_events


def test_collect_upgrades_from_events():
  events = [
    {
      "symbol": "BTC/USDT",
      "style": "smc",
      "prior_status": "monitor",
      "new_status": "executable",
      "upgrade_note": "SMC UPGRADED",
    }
  ]
  queue = [
    {
      "id": "BTC/USDT:smc",
      "symbol": "BTC/USDT",
      "style": "smc",
      "status": "executable",
      "direction": "LONG",
      "check": "15m",
      "execution_tier": "full",
      "entry": 100,
      "stop": 95,
      "tp1": 110,
      "entry_signal": True,
      "oos_win_rate": 0.62,
      "oos_trades": 20,
      "setup_live": {
        "entry_confirm_ok": True,
        "structure_blocked": False,
        "vp_filter_ok": True,
        "oos_gate": "passed",
      },
    }
  ]
  upgrades = collect_monitor_upgrades_from_events(events, queue)
  assert len(upgrades) == 1
  assert upgrades[0]["symbol"] == "BTC/USDT"
  assert upgrades[0]["source"] == "monitor_upgrade"
