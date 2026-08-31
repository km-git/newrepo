"""Tests for OHLC paper simulator."""

from __future__ import annotations

import os

import pytest

from engine.paper_simulator import (
  _parse_as_of,
  _tail_bars,
  extract_legs,
  gate_paper_row,
  limit_fills_on_bar,
  rank_rows,
  run_paper_simulation,
  simulate_trade_on_bars,
  write_paper_pnl_report,
)


def _row(**kwargs):
  base = {
    "symbol": "BTC/USDT",
    "timeframe": "15m",
    "direction": "SHORT",
    "row_type": "primary",
    "gtc_tier": "executable",
    "honest_execution_tier": "full",
    "in_kill_zone": "Y",
    "gtc_size_cap_pct": 100,
    "executive_verdict": "CONDITIONAL_GO",
    "macro_mode": "NEUTRAL",
    "stop_loss": 61000,
    "tp1": 59000,
    "tp1_exit_pct": 50,
    "tp2": 58000,
    "tp2_exit_pct": 30,
    "tp3": 57000,
    "tp3_exit_pct": 20,
    "position_notional_usd": 10000,
    "wae": 60000,
    "dca_legs": [
      {"leg": 1, "price": 60000, "size_pct": 10},
      {"leg": 2, "price": 59800, "size_pct": 20},
    ],
    "leg1_usd": 1000,
    "leg2_usd": 2000,
  }
  base.update(kwargs)
  return base


def test_limit_fill_short():
  assert limit_fills_on_bar("SHORT", 60000, 60100, 59900) is True
  assert limit_fills_on_bar("SHORT", 60000, 59900, 59800) is False


def test_limit_fill_long():
  assert limit_fills_on_bar("LONG", 100, 105, 99) is True
  assert limit_fills_on_bar("LONG", 100, 105, 101) is False


def test_extract_legs():
  legs = extract_legs(_row())
  assert len(legs) == 2
  assert legs[0]["price"] == 60000
  assert legs[0]["usd"] == 1000


def test_simulate_short_tp():
  # Price rises to fill short at 60000, then drops to TP1
  highs = [60100, 60050, 59900, 59500, 59000, 58500]
  lows = [59800, 59700, 59200, 58800, 58500, 58000]
  result = simulate_trade_on_bars(_row(), highs, lows, fee=0.0)
  assert result["legs_filled"] >= 1
  assert result["status"] in ("closed_tp", "closed_sl", "open")
  assert result["realized_pnl_usd"] != 0 or result["status"] == "no_fill"


def test_simulate_short_sl():
  highs = [60500, 61000, 61500]
  lows = [60000, 60800, 61200]
  result = simulate_trade_on_bars(_row(), highs, lows, fee=0.0)
  if result["legs_filled"] > 0:
    assert result["status"] == "closed_sl"


def test_gate_requires_kill_zone(monkeypatch):
  monkeypatch.setenv("EW_PAPER_REQUIRE_KILL_ZONE", "1")
  monkeypatch.setenv("EW_TACTICAL_SAFEGUARD", "0")
  ok, reasons = gate_paper_row(_row(in_kill_zone="N"))
  assert ok is False
  assert "not_in_kill_zone" in reasons


def test_gate_max_positions(monkeypatch):
  monkeypatch.setenv("EW_PAPER_MAX_POSITIONS", "3")
  ok, _ = gate_paper_row(_row(), open_positions=3)
  assert ok is False


def test_rank_full_before_probe():
  rows = [
    _row(honest_execution_tier="probe"),
    _row(honest_execution_tier="full"),
  ]
  ranked = rank_rows(rows)
  assert ranked[0]["honest_execution_tier"] == "full"


def test_parse_as_of_end_of_day():
  dt = _parse_as_of("2026-08-15")
  assert dt is not None
  assert dt.hour == 23 and dt.minute == 59


def test_tail_bars_requires_minimum():
  import pandas as pd

  idx = pd.date_range("2026-01-01", periods=3, freq="h", tz="UTC")
  df = pd.DataFrame({"High": [1, 2, 3], "Low": [0.5, 1.5, 2.5]}, index=idx)
  highs, lows = _tail_bars(df, 10)
  assert highs == []


def test_skip_no_ohlc_fills_next_candidate(monkeypatch):
  monkeypatch.setenv("EW_PAPER_MAX_POSITIONS", "2")
  monkeypatch.setenv("EW_PAPER_REQUIRE_KILL_ZONE", "0")
  monkeypatch.setenv("EW_PAPER_DISABLE_TFS", "")
  monkeypatch.setenv("EW_TACTICAL_SAFEGUARD", "0")

  rows = [
    _row(symbol="BAD/USDT", honest_execution_tier="full", in_kill_zone="Y"),
    _row(symbol="GOOD/USDT", honest_execution_tier="full", in_kill_zone="Y"),
  ]

  def fake_fetch(sym, tfs, is_crypto=True):
    import pandas as pd

    if sym == "BAD/USDT":
      return {"15m": pd.DataFrame()}
    idx = pd.date_range("2026-01-01", periods=20, freq="h", tz="UTC")
    df = pd.DataFrame(
      {"High": [61000] * 20, "Low": [59000] * 20},
      index=idx,
    )
    return {"15m": df}

  monkeypatch.setattr("engine.paper_simulator._fetch_ohlc_frame", lambda sym, tf, cache, fetch_ohlc=True: fake_fetch(sym, [tf]).get(tf))

  summary = run_paper_simulation(rows=rows, fetch_ohlc=True, write_report=False)
  assert summary["simulated"] == 1
  assert summary["skipped_count"] == 1
  assert summary["trades"][0]["symbol"] == "GOOD/USDT"


def test_write_report(tmp_path):
  summary = {
    "run_at": "2026-01-01T00:00:00+00:00",
    "starting_equity_usd": 50000,
    "ending_equity_usd": 50100,
    "realized_pnl_usd": 100,
    "fees_usd": 5,
    "fee_rate": 0.0026,
    "max_positions": 3,
    "candidates": 10,
    "simulated": 3,
    "blocked_count": 7,
    "wins": 2,
    "losses": 1,
    "no_fill": 0,
    "trades": [
      {
        "symbol": "BTC/USDT",
        "timeframe": "15m",
        "honest_execution_tier": "full",
        "status": "closed_tp",
        "legs_filled": 2,
        "legs_total": 2,
        "realized_pnl_usd": 100,
        "fees_usd": 5,
        "avg_entry": 59900,
      }
    ],
    "blocked": [],
  }
  out = tmp_path / "PAPER_PNL.md"
  write_paper_pnl_report(summary, path=out)
  text = out.read_text()
  assert "Paper Execution P&L" in text
  assert "BTC/USDT" in text
