"""Tests for profit laboratory."""

from __future__ import annotations

import json
from pathlib import Path

import pandas as pd
import pytest

from engine.profit_lab.expectancy import build_expectancy_report, compute_slice_expectancy
from engine.profit_lab.runner import composite_verdict
from engine.profit_lab.setup_returns import net_r_from_setup, setups_to_returns_frame


def _sample_setup(status="tp1_hit", tf="1h", direction="LONG", wae=100.0, stop=95.0, tp1=110.0):
  return {
    "id": f"BTC/USDT|{tf}|{direction}",
    "symbol": "BTC/USDT",
    "timeframe": tf,
    "direction": direction,
    "status": status,
    "wae": wae,
    "stop_loss": stop,
    "tp1": tp1,
    "resolved_at": "2026-01-15T12:00:00+00:00",
  }


def test_net_r_from_setup_sl():
  r = net_r_from_setup(_sample_setup(status="sl_hit"))
  assert r is not None
  assert r < 0


def test_net_r_from_setup_tp():
  r = net_r_from_setup(_sample_setup())
  assert r is not None


def test_setups_to_returns_frame():
  closed = [_sample_setup(), _sample_setup(status="sl_hit", tf="4h")]
  df = setups_to_returns_frame(closed, apply_policy=False)
  assert len(df) == 2
  assert "net_r" in df.columns


def test_compute_slice_expectancy(monkeypatch):
  monkeypatch.setenv("EW_EXPECTANCY_MIN_SAMPLES", "1")
  rows = [
    {"pair_tf": "BTC/USDT|1h", "timeframe": "1h", "direction": "LONG", "net_r": 0.5},
    {"pair_tf": "BTC/USDT|1h", "timeframe": "1h", "direction": "LONG", "net_r": -0.2},
    {"pair_tf": "ETH/USDT|4h", "timeframe": "4h", "direction": "SHORT", "net_r": -1.0},
  ]
  df = pd.DataFrame(rows)
  slices = compute_slice_expectancy(df, dimensions=("timeframe",), min_n=1)
  by_tf = {s["slice"]: s for s in slices}
  assert by_tf["1h"]["expectancy_r"] == pytest.approx(0.15, abs=0.01)
  assert by_tf["4h"]["passes_gate"] is False


def test_composite_verdict_profit_go():
  v = composite_verdict(
    expectancy={"overall": {"passes_gate": True, "expectancy_r": 0.1}},
    cpcv={"deployment_gate": {"verdict": "GO", "passed": True}},
    cost={"equity_start": 50_000, "equity_end": 55_000},
  )
  assert v["verdict"] == "PROFIT_GO"


def test_composite_verdict_no_go():
  v = composite_verdict(
    expectancy={"overall": {"passes_gate": False, "expectancy_r": -0.1}},
    cpcv={"deployment_gate": {"verdict": "NO_GO", "passed": False}},
    cost={"equity_start": 50_000, "equity_end": 40_000},
  )
  assert v["verdict"] == "PROFIT_NO_GO"


def test_run_profit_lab_offline(monkeypatch, tmp_path):
  monkeypatch.setenv("EW_PROFIT_LAB_REPORT", str(tmp_path / "pl.md"))
  monkeypatch.setenv("EW_PROFIT_LAB_STATE", str(tmp_path / "pl.json"))
  monkeypatch.setenv("EW_PROFIT_LAB_HTML", str(tmp_path / "ts.html"))
  monkeypatch.setenv("EW_PROFIT_LAB_COST_JSON", str(tmp_path / "cost.json"))
  monkeypatch.setenv("EW_EXPECTANCY_STATE", str(tmp_path / "exp.json"))
  monkeypatch.setenv("EW_PROFIT_LAB_SWEEP", "0")

  closed = [_sample_setup() for _ in range(40)] + [
    _sample_setup(status="sl_hit", tf="4h") for _ in range(10)
  ]
  for i, s in enumerate(closed):
    s["resolved_at"] = f"2026-01-{1 + i % 28:02d}T12:00:00+00:00"

  def fake_frame(**kwargs):
    return setups_to_returns_frame(closed, apply_policy=False)

  monkeypatch.setattr("engine.profit_lab.setup_returns.setups_to_returns_frame", fake_frame)

  from engine.profit_lab.runner import run_profit_lab

  result = run_profit_lab(run_sweep=False, write_reports=True)
  assert "readiness" in result
  assert (tmp_path / "pl.md").exists()


def test_freqtrade_export(tmp_path, monkeypatch):
  monkeypatch.setenv("EW_FREQTRADE_EXPORT", str(tmp_path / "signals.json"))
  from engine.freqtrade_export import export_freqtrade_signals

  rows = [{
    "symbol": "BTC/USDT",
    "timeframe": "1h",
    "direction": "LONG",
    "wae": 100,
    "stop_loss": 95,
    "tp1": 110,
    "gtc_tier": "executable",
  }]
  out = export_freqtrade_signals(rows=rows, output_path=tmp_path / "signals.json")
  assert out["signal_count"] == 1
  data = json.loads((tmp_path / "signals.json").read_text())
  assert data["signals"][0]["pair"] == "BTC/USDT"
