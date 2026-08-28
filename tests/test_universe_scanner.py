"""Tests for universe scanner and timeframe constants."""

from __future__ import annotations

import json
from pathlib import Path

from engine.timeframes import BOARD_TIMEFRAMES, DEFAULT_TFS, UNIVERSE_TFS
from engine.universe_scanner import (
  _chunk_pairs,
  merge_results,
  run_universe_tick,
  save_state,
)


def test_universe_tfs_include_12h():
  assert "12h" in UNIVERSE_TFS
  assert "12h" in DEFAULT_TFS
  assert "12h" in BOARD_TIMEFRAMES
  assert len(UNIVERSE_TFS) == 6


def test_chunk_pairs_rotation():
  pairs = [f"P{i}/USDT" for i in range(10)]
  c0 = _chunk_pairs(pairs, 3, 0)
  c1 = _chunk_pairs(pairs, 3, 1)
  c3 = _chunk_pairs(pairs, 3, 3)
  c4 = _chunk_pairs(pairs, 3, 4)
  assert c0 == ["P0/USDT", "P1/USDT", "P2/USDT"]
  assert c1 == ["P3/USDT", "P4/USDT", "P5/USDT"]
  assert c3 == ["P9/USDT"]
  assert c4 == c0  # wraps after 4 chunks


def test_merge_results_by_symbol():
  existing = {"BTC/USDT": {"symbol": "BTC/USDT", "status": "old"}}
  new = [{"symbol": "ETH/USDT", "status": "new"}, {"symbol": "BTC/USDT", "status": "updated"}]
  merged = merge_results(existing, new)
  assert merged["BTC/USDT"]["status"] == "updated"
  assert merged["ETH/USDT"]["status"] == "new"


def test_universe_tick_state_persists(tmp_path, monkeypatch):
  state_path = tmp_path / "universe_state.json"
  results_path = tmp_path / "universe_results.json"
  pairs_cache = tmp_path / "universe_pairs.json"

  monkeypatch.setattr("engine.universe_scanner.STATE_PATH", state_path)
  monkeypatch.setattr("engine.universe_scanner.RESULTS_PATH", results_path)
  monkeypatch.setattr("engine.universe_scanner.PAIRS_CACHE", pairs_cache)
  monkeypatch.setattr(
    "engine.universe_scanner.refresh_universe_pairs",
    lambda n, quote, force=False: ["BTC/USDT", "ETH/USDT"],
  )
  monkeypatch.setattr(
    "engine.universe_scanner.run_pairs_chunk",
    lambda pairs, tfs, output_dir: [
      {"symbol": p, "status": "active", "step8_outcomes": {"setups": {}}}
      for p in pairs
    ],
  )
  monkeypatch.setattr(
    "engine.universe_scanner.finalize_universe_cycle",
    lambda results, output_dir, paper_max: {"board_picks": 2, "best_trades_csv": "x.csv"},
  )

  r1 = run_universe_tick(universe_size=2, chunk_size=1, output_dir=str(tmp_path))
  assert r1["chunk_pairs"] == 1
  assert state_path.exists()
  state = json.loads(state_path.read_text())
  assert state["chunk_index"] == 1

  r2 = run_universe_tick(universe_size=2, chunk_size=1, output_dir=str(tmp_path))
  assert r2["finalized"] is True
  assert r2["cycle"] == 1
