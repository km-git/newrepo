"""Tests for SMC monitor and execution queue."""

from __future__ import annotations

from unittest.mock import MagicMock, patch

import pandas as pd

from engine.execution_queue import build_execution_queue, collect_board_candidates
from engine.portfolio_manager import approve_candidates


def _ohlc(n=50, close=100.0):
  rows = [[close, close + 1, close - 1, close, 1.0] for _ in range(n)]
  return pd.DataFrame(rows, columns=["Open", "High", "Low", "Close", "Volume"])


def test_collect_board_execute_now():
  board = {
    "picks": [
      {
        "symbol": "BTC/USDT",
        "style": "smc",
        "timeframe": "15m",
        "direction": "LONG",
        "executive_action": "EXECUTE_NOW",
        "pipeline_status": "executable",
        "execution_tier": "full",
        "executive_score": 80,
        "position_size_pct": 100,
        "entry": 100.0,
        "stop_loss": 95.0,
        "stop_pct": 5.0,
        "entry_signal": True,
        "tags": "liquidity sweep, VP filter pass",
      },
      {
        "symbol": "ETH/USDT",
        "style": "swing",
        "executive_action": "WATCH_ONLY",
        "pipeline_status": "monitor",
        "executive_score": 40,
      },
    ]
  }
  cands = collect_board_candidates(board)
  assert len(cands) == 1
  assert cands[0]["symbol"] == "BTC/USDT"
  assert cands[0]["calibrated_size_pct"] <= 100


def test_portfolio_rejects_duplicate():
  open_pos = [{"symbol": "BTC/USDT", "style": "smc", "size_factor": 0.5}]
  cands = [{"symbol": "BTC/USDT", "style": "smc", "calibrated_size_pct": 50, "stop_pct": 1.0}]
  approved, rejected = approve_candidates(cands, open_pos=open_pos, max_concurrent=8)
  assert len(approved) == 0
  assert len(rejected) == 1


@patch("engine.smc_monitor.build_institutional_matrix")
@patch("engine.smc_monitor.validate_msb_zscore")
@patch("engine.smc_monitor.load_calibration")
def test_smc_monitor_upgrade(mock_cal, mock_msb, mock_inst):
  mock_cal.return_value = {"available": False}
  mock_msb.return_value = {"status": "ok", "pass": False, "z": 0.5}
  mock_inst.return_value = {
    "entry_signal": True,
    "entry_probe": False,
    "entry_grade": "A",
    "confluence_count": 3,
    "best_entry_tf": "15m",
    "by_tf": {
      "15m": {
        "status": "ok",
        "entry_signal": True,
        "entry_grade": "A",
        "score": 70,
        "tags": ["liquidity sweep"],
        "structure_event": "BOS",
        "vp_filter_ok": True,
        "recent_sweep": True,
        "active_ob": {"top": 101, "bot": 99},
      }
    },
  }
  from engine.smc_monitor import evaluate_smc_triggers

  df = _ohlc()
  item = {
    "symbol": "TEST/USDT",
    "style": "smc",
    "status": "monitor",
    "direction": "LONG",
    "check": "15m",
    "entry_zone": [99, 101],
    "stop": 95,
    "tp1": 110,
  }
  result = evaluate_smc_triggers(item, {"15m": df})
  assert result.get("entry_signal") is True
  assert "SMC entry_signal" in " ".join(result.get("triggers_hit", []))


def test_build_execution_queue_dedupes():
  board = {
    "picks": [
      {
        "symbol": "BTC/USDT",
        "style": "smc",
        "executive_action": "EXECUTE_NOW",
        "pipeline_status": "executable",
        "execution_tier": "full",
        "executive_score": 80,
        "position_size_pct": 100,
        "timeframe": "15m",
        "direction": "LONG",
        "entry": 100,
        "stop_loss": 95,
        "tags": "",
      }
    ]
  }
  monitor = [
    {
      "id": "BTC/USDT:smc",
      "symbol": "BTC/USDT",
      "style": "smc",
      "prior_status": "monitor",
      "new_status": "executable",
      "execution_tier": "full",
      "direction": "LONG",
      "check": "15m",
      "entry": 100,
      "stop": 95,
      "entry_signal": True,
    }
  ]
  eq = build_execution_queue(board=board, monitor_queue=monitor, approve=False)
  assert eq["deduped_count"] == 1
