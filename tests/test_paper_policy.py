"""Tests for learned paper execution policy."""

from __future__ import annotations

import json

from engine.paper_policy import (
  is_symbol_blocked,
  learn_symbol_policy,
  major_symbols,
  record_paper_trades,
  refresh_paper_policy,
  symbol_blocklist,
)


def test_major_symbols_includes_btc_eth(tmp_path, monkeypatch):
  monkeypatch.delenv("EW_PAPER_MAJOR_SYMBOLS", raising=False)
  majors = major_symbols()
  assert "BTC/USDT" in majors
  assert "ETH/USDT" in majors


def test_env_junk_blocklist(monkeypatch):
  monkeypatch.setenv("EW_PAPER_JUNK_SYMBOLS", "GRVT/USDT,CHIP/USDT")
  monkeypatch.setenv("EW_PAPER_SYMBOL_BLOCKLIST", "")
  blocked = symbol_blocklist()
  assert "GRVT/USDT" in blocked
  assert is_symbol_blocked("GRVT/USDT")


def test_learn_blocks_repeat_losers(tmp_path, monkeypatch):
  trades = tmp_path / "trades.jsonl"
  policy = tmp_path / "policy.json"
  monkeypatch.setenv("EW_PAPER_TRADES_LOG", str(trades))
  monkeypatch.setenv("EW_PAPER_LEARNED_POLICY", str(policy))
  monkeypatch.setenv("EW_PAPER_JUNK_SYMBOLS", "")
  monkeypatch.setenv("EW_PAPER_LEARN_MIN_TRADES", "2")
  monkeypatch.setenv("EW_PAPER_LEARN_MIN_LOSS_USD", "5")

  summary = {
    "run_at": "2026-01-01T00:00:00+00:00",
    "trades": [
      {"symbol": "ZZZ/USDT", "timeframe": "15m", "status": "closed_sl", "realized_pnl_usd": -10},
      {"symbol": "ZZZ/USDT", "timeframe": "15m", "status": "closed_sl", "realized_pnl_usd": -8},
    ],
  }
  record_paper_trades(summary)
  learned = learn_symbol_policy()
  assert "ZZZ/USDT" in learned["block_symbols"]


def test_refresh_writes_policy(tmp_path, monkeypatch):
  monkeypatch.setenv("EW_PAPER_TRADES_LOG", str(tmp_path / "t.jsonl"))
  monkeypatch.setenv("EW_PAPER_LEARNED_POLICY", str(tmp_path / "p.json"))
  monkeypatch.setenv("EW_PAPER_POLICY_REPORT", str(tmp_path / "r.md"))
  monkeypatch.setenv("EW_PAPER_JUNK_SYMBOLS", "X/USDT")
  policy = refresh_paper_policy()
  assert (tmp_path / "p.json").exists()
  assert "X/USDT" in policy["block_symbols"]
