"""Live fill reconciliation tests."""

from __future__ import annotations

import json

from engine.fill_tracker import parse_client_id, reconcile_fill_to_setup, reconcile_live_fills


def test_parse_client_id_stop():
  parsed = parse_client_id("ew-BTCUSDT-1d-L9-sl")
  assert parsed is not None
  assert parsed["sym_compact"] == "BTCUSDT"
  assert parsed["timeframe"] == "1d"
  assert parsed["outcome"] == "sl_hit"


def test_reconcile_fill_matches_open_setup(tmp_path, monkeypatch):
  import engine.fill_tracker as ft
  import engine.outcome_tracker as ot

  tracked = tmp_path / "tracked.json"
  fills = tmp_path / "fills.jsonl"
  reconciled = tmp_path / "reconciled.json"
  monkeypatch.setattr(ot, "TRACKED_PATH", tracked)
  monkeypatch.setattr(ft, "FILLS_PATH", fills)
  monkeypatch.setattr(ft, "_RECONCILED_PATH", reconciled)

  tracked.write_text(json.dumps({
    "open": [{
      "id": "BTC/USDT|1d|LONG",
      "symbol": "BTC/USDT",
      "timeframe": "1d",
      "direction": "LONG",
      "status": "open",
    }],
    "closed": [],
  }))

  fill = {"client_id": "ew-BTCUSDT-1d-L9-sl", "price": 90000, "side": "sell"}
  match = reconcile_fill_to_setup(fill)
  assert match is not None
  assert match["setup_id"] == "BTC/USDT|1d|LONG"

  fills.write_text(json.dumps(fill) + "\n")
  matches = reconcile_live_fills()
  assert len(matches) == 1
