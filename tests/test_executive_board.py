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


def test_board_empty_when_no_honesty_executables():
  results = []
  styles = {"scalp": "15m", "day_trade": "1h", "swing": "1d", "long_term": "1w"}
  for sym in ["BTC/USDT", "ETH/USDT"]:
    setups = {style: _setup(oos_win_rate=0.58, readiness_score=80) for style in styles}
    results.append({
      "symbol": sym,
      "status": "active",
      "executive_decision": {"verdict": "STAGED_GO"},
      "step6_wave_consensus": {"consensus_direction": "BULL", "agreement_pct": 65},
      "step8_outcomes": {"setups": setups},
    })

  board = build_executive_board(results)
  assert board["board_picks"] == 0
  assert board["by_action"].get("EXECUTE_NOW", 0) == 0
  assert len(board["all_ranked"]) > 0


def test_board_execute_now_matches_honesty_validated():
  ex = _setup(
    status="executable",
    execution_tier="probe",
    oos_win_rate=0.67,
    oos_trades=12,
    oos_gate="passed",
    direction="SHORT",
    stop_loss={"price": 108, "distance_pct": 3},
    entry={"anchor": 100, "order_type": "limit", "zone": [99, 101]},
    targets=[{"price": 95, "rr": 1}, {"price": 90, "rr": 2}],
  )
  results = [{
    "symbol": "ZEC/USDT",
    "status": "active",
    "executive_decision": {"verdict": "GO"},
    "step6_wave_consensus": {"consensus_direction": "BEAR", "agreement_pct": 80},
    "step8_outcomes": {"setups": {"scalp": ex}},
  }]
  board = build_executive_board(results)
  exec_now = [p for p in board["picks"] if p["executive_action"] == "EXECUTE_NOW"]
  assert len(exec_now) == 1
  assert board["by_action"].get("EXECUTE_NOW") == 1


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
