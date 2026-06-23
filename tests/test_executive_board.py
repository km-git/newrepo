"""Tests for executive trade board."""

from __future__ import annotations

from engine.executive_board import build_executive_board, save_executive_board


def _setup(**kwargs):
  base = {
    "status": "monitor",
    "execution_tier": "none",
    "direction": "LONG",
    "readiness_score": 65,
    "wave_valid": False,
    "wave_partial": False,
    "oos_win_rate": 0.62,
    "oos_trades": 10,
    "autodream_verdict": "validated",
    "stop_loss": {"price": 95, "distance_pct": 3},
    "entry": {"anchor": 100, "order_type": "limit", "zone": [99, 101]},
    "targets": [{"price": 105, "rr": 1}, {"price": 110, "rr": 2}],
    "honest_reason": "monitor",
    "timeframe": "1d",
  }
  base.update(kwargs)
  return base


def test_board_always_has_picks_per_timeframe():
  results = []
  styles = {"scalp": "15m", "day_trade": "1h", "swing": "1d", "long_term": "1w"}
  for i, sym in enumerate(["BTC/USDT", "ETH/USDT", "SOL/USDT", "ADA/USDT", "DOT/USDT"]):
    setups = {}
    for style, tf in styles.items():
      setups[style] = _setup(
        oos_win_rate=0.58 + i * 0.02,
        readiness_score=60 + i * 3,
      )
    results.append({
      "symbol": sym,
      "status": "active",
      "executive_decision": {"verdict": "STAGED_GO"},
      "step6_wave_consensus": {"consensus_direction": "BULL", "agreement_pct": 65},
      "step8_outcomes": {"setups": setups},
    })

  board = build_executive_board(results, picks_per_tf=3, max_total=20)
  assert board["board_picks"] >= 4
  tfs = {p["timeframe"] for p in board["picks"]}
  assert "15m" in tfs
  assert "1h" in tfs
  assert all(p.get("executive_action") for p in board["picks"])
  assert all(p.get("position_size_pct", 0) > 0 for p in board["picks"])


def test_board_includes_4h_context():
  results = [{
    "symbol": "SOL/USDT",
    "status": "active",
    "executive_decision": {"verdict": "GO"},
    "step6_wave_consensus": {"consensus_direction": "BEAR", "agreement_pct": 70},
    "step2_wave_structure": {
      "4h": {
        "status": "ok",
        "structure": "bear_impulse_5",
        "direction": "BEAR",
        "impulse_valid": True,
        "impulse_partial": False,
      },
    },
    "step8_outcomes": {"setups": {"day_trade": _setup(oos_win_rate=0.6)}},
  }]
  board = build_executive_board(results, picks_per_tf=1, max_total=5)
  tfs = {p["timeframe"] for p in board["picks"]}
  assert "4h" in tfs or any(p.get("is_4h_context") for p in board.get("all_ranked", []))


def test_save_executive_board(tmp_path):
  board = build_executive_board([{
    "symbol": "X/USDT",
    "status": "active",
    "executive_decision": {"verdict": "GO"},
    "step6_wave_consensus": {},
    "step8_outcomes": {"setups": {"swing": _setup(oos_win_rate=0.7)}},
  }])
  paths = save_executive_board(
    board,
    json_path=tmp_path / "board.json",
    csv_path=tmp_path / "board.csv",
  )
  assert (tmp_path / "board.json").exists()
