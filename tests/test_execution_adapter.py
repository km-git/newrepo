"""Tests for execution adapter dry-run and deduplication."""

from __future__ import annotations

import json
from datetime import datetime, timedelta, timezone
from pathlib import Path
from unittest.mock import patch

from engine.execution_adapter import (
  DEDUP_PATH,
  drain_execution_queue,
  filter_fresh_candidates,
  mark_executed_ids,
  preview_execution,
  recently_executed_ids,
)


def test_preview_execution_dry_run_fields():
  cand = {
    "symbol": "BTC/USDT",
    "style": "smc",
    "direction": "LONG",
    "calibrated_size_pct": 50,
    "source": "board",
  }
  p = preview_execution(cand)
  assert p["dry_run"] is True
  assert p["symbol"] == "BTC/USDT"


def test_dedup_filters_recent_ids(tmp_path, monkeypatch):
  dedup = tmp_path / "dedup.json"
  cid = "BTC/USDT:smc"
  mark_executed_ids([cid], path=dedup)
  monkeypatch.setattr("engine.execution_adapter.DEDUP_PATH", dedup)

  fresh, skipped = filter_fresh_candidates(
    [{"id": cid, "symbol": "BTC/USDT", "style": "smc"}],
    hours=24,
  )
  assert len(fresh) == 0
  assert len(skipped) == 1


def test_drain_dry_run_no_ledger(tmp_path, monkeypatch):
  monkeypatch.setattr("engine.execution_adapter.DEDUP_PATH", tmp_path / "dedup.json")
  log_path = tmp_path / "exec_log.jsonl"
  monkeypatch.setattr("engine.execution_adapter.EXEC_LOG_PATH", log_path)

  queue = {
    "approved": [
      {
        "id": "ETH/USDT:smc",
        "symbol": "ETH/USDT",
        "style": "smc",
        "direction": "SHORT",
        "timeframe": "15m",
        "calibrated_size_pct": 25,
        "source": "board",
        "execution_tier": "probe",
        "pipeline_status": "executable",
        "oos_gate": "passed",
        "oos_win_rate": 0.58,
        "oos_trades": 18,
        "entry_confirm_ok": True,
        "structure_blocked": False,
        "vp_filter_ok": True,
      }
    ]
  }
  with patch("engine.execution_adapter.append_paper_ledger") as mock_ledger:
    result = drain_execution_queue(queue, dry_run=True, max_trades=5)
    mock_ledger.assert_not_called()
  assert result["dry_run"] is True
  assert result["executed"] == 1
  assert result["trades"][0]["dry_run"] is True
  assert log_path.exists()


def test_recently_executed_prunes_old(tmp_path):
  dedup = tmp_path / "dedup.json"
  old = (datetime.now(timezone.utc) - timedelta(days=10)).isoformat()
  dedup.write_text(json.dumps({"ids": {"OLD/USDT:smc": old}}))
  recent = recently_executed_ids(hours=24, path=dedup)
  assert "OLD/USDT:smc" not in recent
