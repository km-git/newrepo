"""Tests for ledger-driven indicator calibration and OOS executable gate."""

from __future__ import annotations

import json
from pathlib import Path

import pandas as pd

from core.indicators import collect_indicator_signals, compute_raw_indicators
from engine.indicator_calibration import (
  MIN_OOS_EXECUTABLE,
  SCORING_ERA_CALIBRATED,
  accumulation_status,
  analyze_signal_predictiveness,
  apply_oos_executable_gate,
  build_calibration,
  enrich_ledger_entry,
  filter_calibrated_ledger,
  merge_setup_metadata_into_trades,
  run_calibration_accumulation_cycle,
  run_indicator_calibration,
  score_indicator_confluence_calibrated,
)
from engine.readiness import resolve_execution_status


def _synthetic_ledger(n: int = 80) -> list[dict]:
  rows = []
  for i in range(n):
    win = i % 3 != 0
    reason = (
      "swing PROBE executable: indicators 80/100 (RSI 48 bullish reset zone, MACD histogram rising, in kill zone)"
      if win
      else "Monitor scalp: harmonic PRZ active (RSI 42 weakness intact, price below EMA20/50)"
    )
    rows.append(
      {
        "paper_outcome": "win" if win else "loss",
        "honest_reason": reason,
        "style": "swing" if win else "scalp",
        "readiness_score": 78 if win else 52,
      }
    )
  return rows


def test_analyze_signal_predictiveness():
  stats = analyze_signal_predictiveness(_synthetic_ledger())
  assert stats["available"] is True
  assert stats["closed_trades"] == 80
  assert "kept_signals" in stats
  assert "removed_signals" in stats


def test_build_calibration_has_weights():
  cal = build_calibration(_synthetic_ledger())
  assert cal["available"] is True
  assert cal["signal_weights"]
  assert cal["min_oos_executable"] == MIN_OOS_EXECUTABLE


def test_calibrated_scoring_blocks_removed_signals():
  cal = build_calibration(_synthetic_ledger(120))
  cal["signal_weights"] = {"in kill zone": 25, "RSI bullish reset": 20}
  cal["blocked_signals"] = ["RSI weakness intact", "below EMA20/50", "harmonic PRZ"]
  cal["style_thresholds"] = {"swing": 55}
  cal["available"] = True

  rows = []
  p = 100.0
  for i in range(60):
    p += 0.2
    rows.append({"Open": p, "High": p + 1, "Low": p - 1, "Close": p, "Volume": 1200})
  df = pd.DataFrame(rows)

  r = score_indicator_confluence_calibrated(df, "LONG", 99.5, 100.5, "swing", cal)
  assert r["calibrated"] is True
  assert r.get("hybrid") is True
  assert "RSI weakness intact" not in " ".join(r.get("active_tokens", []))


def test_apply_oos_executable_gate_demotes():
  setup = {
    "status": "executable",
    "execution_tier": "probe",
    "honest_reason": "probe ok",
    "oos_win_rate": 0.48,
    "oos_trades": 12,
  }
  out = apply_oos_executable_gate(dict(setup))
  assert out["status"] == "monitor"
  assert out["execution_tier"] == "none"
  assert out["oos_gate"] == "below_threshold"


def test_apply_oos_executable_gate_passes():
  setup = {
    "status": "executable",
    "execution_tier": "full",
    "honest_reason": "full ok",
    "oos_win_rate": 0.58,
    "oos_trades": 10,
  }
  out = apply_oos_executable_gate(dict(setup))
  assert out["status"] == "executable"
  assert out["oos_gate"] == "passed"


def test_resolve_execution_status_oos_gate():
  status, tier, reason = resolve_execution_status(
    style="swing",
    direction="LONG",
    wave={"structure": "impulse", "impulse_valid": True},
    in_zone=True,
    zone_dist_pct=0.0,
    impulse_valid=True,
    consensus_dir="LONG",
    rr=2.0,
    min_rr=1.5,
    harmonic_near=False,
    indicator={"score": 80, "aligned": True, "threshold": 55, "signals": []},
    executive_verdict="GO",
    oos_win_rate=0.50,
    oos_trades=8,
  )
  assert status == "monitor"
  assert "OOS gate" in reason


def test_run_indicator_calibration_writes(tmp_path, monkeypatch):
  ledger = tmp_path / "ledger.jsonl"
  with ledger.open("w") as f:
    for row in _synthetic_ledger(60):
      f.write(json.dumps(row) + "\n")

  out = tmp_path / "calibration.json"
  monkeypatch.setattr(
    "engine.indicator_calibration.PAPER_LEDGER_DEFAULT",
    ledger,
  )
  monkeypatch.setattr(
    "engine.indicator_calibration.CALIBRATION_PATH",
    out,
  )
  cal = run_indicator_calibration()
  assert cal.get("available")
  assert out.exists()


def test_collect_indicator_signals_tokens():
  raw = {
    "price": 100.0,
    "rsi14": 48.0,
    "ema20": 99.0,
    "ema50": 98.0,
    "macd_hist": 0.1,
    "macd_hist_delta": 0.02,
    "volume_ratio": 1.4,
    "above_ema20": True,
    "above_ema50": True,
  }
  tokens = [t for t, _ in collect_indicator_signals(raw, "LONG", 0.0)]
  assert "in kill zone" in tokens
  assert "RSI bullish reset" in tokens


def test_enrich_ledger_entry_tags_calibrated_era():
  cal = build_calibration(_synthetic_ledger(80))
  setup = {
    "indicators": {"calibrated": True, "active_tokens": ["in kill zone", "MACD rising"]},
    "oos_win_rate": 0.62,
    "oos_trades": 8,
    "oos_gate": "passed",
  }
  trade = enrich_ledger_entry({"symbol": "BTC/USDT", "style": "swing"}, setup, cal)
  assert trade["scoring_era"] == SCORING_ERA_CALIBRATED
  assert trade["indicator_tokens"] == ["in kill zone", "MACD rising"]
  assert trade["calibration_id"]


def test_accumulation_status_counts_eras():
  ledger = []
  for i in range(40):
    ledger.append({"paper_outcome": "win", "scoring_era": SCORING_ERA_CALIBRATED})
  for i in range(20):
    ledger.append({"paper_outcome": "loss"})
  status = accumulation_status(ledger)
  assert status["calibrated_closed"] == 40
  assert status["legacy_closed"] == 20
  assert status["remaining_to_target"] == 60


def test_filter_calibrated_ledger():
  ledger = [
    {"scoring_era": SCORING_ERA_CALIBRATED, "paper_outcome": "win"},
    {"paper_outcome": "loss"},
  ]
  assert len(filter_calibrated_ledger(ledger)) == 1


def test_merge_setup_metadata_into_trades():
  results = [{
    "symbol": "ETH/USDT",
    "status": "active",
    "step8_outcomes": {
      "setups": {
        "swing": {
          "indicators": {"calibrated": True, "active_tokens": ["near zone"]},
          "oos_win_rate": 0.57,
          "oos_trades": 6,
          "oos_gate": "passed",
        },
      },
    },
  }]
  trades = [{"symbol": "ETH/USDT", "style": "swing", "paper_outcome": "win"}]
  merged = merge_setup_metadata_into_trades(trades, results)
  assert merged[0]["scoring_era"] == SCORING_ERA_CALIBRATED
  assert merged[0]["indicator_tokens"] == ["near zone"]


def test_run_calibration_accumulation_cycle_reestimates(tmp_path, monkeypatch):
  ledger = tmp_path / "ledger.jsonl"
  rows = []
  for i in range(110):
    rows.append({
      "paper_outcome": "win" if i % 2 == 0 else "loss",
      "scoring_era": SCORING_ERA_CALIBRATED,
      "honest_reason": "swing PROBE (RSI 48 bullish reset zone, MACD histogram rising, in kill zone)",
      "indicator_tokens": ["in kill zone", "RSI bullish reset", "MACD rising"],
      "style": "swing",
      "readiness_score": 75,
    })
  ledger.write_text("\n".join(json.dumps(r) for r in rows) + "\n")

  cal_path = tmp_path / "calibration.json"
  acc_path = tmp_path / "accumulation.json"
  monkeypatch.setattr("engine.indicator_calibration.PAPER_LEDGER_DEFAULT", ledger)
  monkeypatch.setattr("engine.indicator_calibration.CALIBRATION_PATH", cal_path)
  monkeypatch.setattr("engine.indicator_calibration.ACCUMULATION_PATH", acc_path)

  status = run_calibration_accumulation_cycle(force_reestimate=True)
  assert status["reestimated"] is True
  assert cal_path.exists()
  saved = json.loads(cal_path.read_text())
  assert saved.get("source") == "calibrated_era_only"
  assert saved.get("calibration_generation", 0) >= 1
