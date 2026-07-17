"""Tests for browser monitor dashboard state builder."""

from __future__ import annotations

from engine.monitor_dashboard import build_dashboard_state, publish_monitor, write_monitor_html


def test_build_dashboard_state_from_fixture_output(tmp_path, monkeypatch):
  out = tmp_path / "output"
  ad = out / "autodream"
  ad.mkdir(parents=True)
  (out / "latest_summary.csv").write_text(
    "symbol,status,verdict,direction,action,confidence\n"
    "BTC/USDT,execute,GO,LONG,execute_long,0.71\n"
  )
  (ad / "monitor_queue.json").write_text(
    '{"updated":"2026-01-01T00:00:00+00:00","queue":[{"symbol":"BTC/USDT","style":"scalp","status":"executable","direction":"LONG","entry":1,"stop":0.9,"tp1":1.1,"check":"15m"}]}'
  )
  (ad / "metrics.json").write_text(
    '{"updated":"2026-01-01T00:00:00+00:00","overall":{"wins":1,"losses":0,"decided":1,"win_rate":1.0}}'
  )

  state = build_dashboard_state(str(out))
  assert state["pairs_count"] == 1
  assert state["by_verdict"]["GO"] == 1
  assert state["queue"]["executable"] == 1
  assert state["metrics"]["win_rate"] == 1.0
  assert len(state["executable_queue"]) == 1


def test_publish_monitor_writes_files(tmp_path):
  out = tmp_path / "output"
  ad = out / "autodream"
  ad.mkdir(parents=True)
  (out / "latest_summary.csv").write_text("symbol,status,verdict\nETH/USDT,active_monitor,STANDBY_ORDERS\n")
  (ad / "monitor_queue.json").write_text('{"queue":[]}')

  paths = publish_monitor(str(out))
  assert (out / "monitor.html").exists()
  assert (ad / "dashboard_state.json").exists()
  assert "monitor_html" in paths


def test_write_monitor_html(tmp_path):
  path = write_monitor_html(str(tmp_path))
  assert path.exists()
  assert "EW Monitor" in path.read_text()
