"""Tests for monetization strategy services reporting."""

from __future__ import annotations

import json
import subprocess
import sys

from engine.monetization_strategy import build_monetization_strategy, save_monetization_strategy


def _best_trades(path, *, executable_scanned=35, top_n=12):
  payload = {
    "timestamp_utc": "2026-09-05T00:00:00+00:00",
    "executable_scanned": executable_scanned,
    "top_n": top_n,
    "top_10": [
      {"symbol": "BTC/USDT", "timeframe": "1h", "score": 88.0},
      {"symbol": "ETH/USDT", "timeframe": "4h", "score": 78.0},
    ],
  }
  path.write_text(json.dumps(payload), encoding="utf-8")
  return path


def test_build_monetization_strategy_design_without_source(tmp_path):
  missing = tmp_path / "missing.json"
  report = build_monetization_strategy(best_trades_path=missing, include_runtime=False)
  assert report["module"] == "monetize"
  assert report["commercial_stage"] == "design"
  assert "research_briefings" in report["summary"]["ready_services"]
  assert report["blockers"]


def test_build_monetization_strategy_pilot_from_best_trades(tmp_path):
  source = _best_trades(tmp_path / "best.json")
  report = build_monetization_strategy(best_trades_path=source, include_runtime=False)
  assert report["commercial_stage"] == "pilot"
  assert "signal_feed" in report["summary"]["ready_services"]
  assert "white_label_api" in report["summary"]["ready_services"]
  assert "signals.internal_use" in report["license_tags"]
  assert report["royalty_reporting"]["minimum_fields"]


def test_build_monetization_strategy_scale_enables_dataset(tmp_path):
  source = _best_trades(tmp_path / "best.json", executable_scanned=150, top_n=40)
  report = build_monetization_strategy(best_trades_path=source, include_runtime=False)
  ready = report["summary"]["ready_services"]
  assert report["commercial_stage"] == "scale"
  assert "derived_dataset" in ready
  assert not any("Derived datasets" in b for b in report["blockers"])


def test_save_monetization_strategy_persists(tmp_path, monkeypatch):
  import engine.monetization_strategy as ms

  out = tmp_path / "monetization.json"
  monkeypatch.setattr(ms, "MONETIZATION_PATH", out)
  report = build_monetization_strategy(best_trades_path=tmp_path / "missing.json", include_runtime=False)
  path = save_monetization_strategy(report)
  assert path == str(out)
  assert json.loads(out.read_text(encoding="utf-8"))["module"] == "monetize"


def test_cli_monetize_outputs_json(tmp_path, monkeypatch):
  out = tmp_path / "monetization.json"
  source = _best_trades(tmp_path / "best.json")
  monkeypatch.setenv("EW_MONETIZATION_PATH", str(out))
  proc = subprocess.run(
    [
      sys.executable,
      "ew_tool.py",
      "--monetize",
      "--monetization-best-trades",
      str(source),
    ],
    check=True,
    capture_output=True,
    text=True,
  )
  data = json.loads(proc.stdout)
  assert data["commercial_stage"] == "pilot"
  assert out.exists()
  assert "[monetize] saved" in proc.stderr
