"""Tests for unified Setup Quality Score (SQS)."""

from __future__ import annotations

import csv
from pathlib import Path

import pytest

from engine.setup_quality_score import (
  compute_setup_quality_score,
  rank_rows_by_sqs,
  save_sqs_ranked_csv,
  sqs_action,
  sqs_tier,
  stamp_row_sqs,
)


def _sample_row(**overrides) -> dict:
  base = {
    "row_type": "primary",
    "geometry_valid": "Y",
    "symbol": "BTC/USDT",
    "timeframe": "1h",
    "direction": "SHORT",
    "gtc_tier": "executable",
    "honest_execution_tier": "probe",
    "executive_verdict": "STAGED_GO",
    "wave_valid": "Y",
    "in_kill_zone": "Y",
    "wave_structure": "impulse_down",
    "agreement_pct": 72,
    "consensus": "BEAR",
    "readiness_score": 68,
    "rr_tp2": 2.5,
    "min_rr": 1.3,
    "tp1_r_multiple": 1.5,
    "wae": 100.0,
    "stop_loss": 102.0,
    "tp1": 97.0,
    "tp2": 95.0,
    "tp3": 92.0,
    "hist_win_rate": 0.62,
    "hist_n": 8,
    "hist_scope": "pair_tf",
    "hist_action": "boost",
    "dca_sl_resolvable": "Y",
    "dca_stop_reduction_pct": 0.9,
    "stop_distance_pct": 2.3,
    "l1_stop_distance_pct": 3.2,
    "executive_action": "EXECUTE_CAUTION",
    "executive_score": 71,
  }
  base.update(overrides)
  return base


def test_sqs_tier_bands():
  assert sqs_tier(80) == "EXECUTE"
  assert sqs_tier(65) == "STANDBY"
  assert sqs_tier(50) == "WATCH"
  assert sqs_tier(30) == "SKIP"


def test_sqs_action_respects_executive():
  row = _sample_row(executive_action="SCALE_IN")
  assert sqs_action(78, row) == "SCALE_IN"
  row = _sample_row(executive_action="WATCH_ONLY")
  assert sqs_action(50, row) == "WATCH_ALERT"


def test_compute_setup_quality_score_high_confluence():
  m = compute_setup_quality_score(_sample_row())
  assert m["sqs_score"] >= 60
  assert m["sqs_tier"] in ("EXECUTE", "STANDBY", "WATCH")
  assert m["sqs_tags"]
  assert "structure" in m["sqs_components_json"]


def test_compute_setup_quality_score_weak_setup():
  m = compute_setup_quality_score(_sample_row(
    wave_valid="N",
    in_kill_zone="N",
    agreement_pct=30,
    consensus="BULL",
    direction="SHORT",
    readiness_score=35,
    hist_win_rate=0.38,
    hist_n=10,
    hist_action="downgrade",
    gtc_tier="watch",
    executive_verdict="STANDBY_ORDERS",
  ))
  assert m["sqs_score"] < 55
  assert m["sqs_tier"] in ("WATCH", "SKIP")


def test_stamp_row_sqs_attaches_fields():
  row = _sample_row()
  stamp_row_sqs(row)
  assert "sqs_score" in row
  assert "sqs_tier" in row
  assert "sqs_action" in row


def test_rank_rows_by_sqs_orders_descending():
  rows = [
    _sample_row(symbol="LOW/USDT", readiness_score=40, hist_win_rate=0.4, hist_n=5),
    _sample_row(symbol="HIGH/USDT", readiness_score=85, hist_win_rate=0.7, hist_n=12),
  ]
  ranked = rank_rows_by_sqs(rows)
  assert ranked[0]["symbol"] == "HIGH/USDT"
  assert ranked[0]["sqs_rank"] == 1
  assert ranked[1]["sqs_rank"] == 2
  assert ranked[0]["sqs_score"] > ranked[1]["sqs_score"]


def test_save_sqs_ranked_csv(tmp_path: Path):
  rows = [_sample_row(symbol="A/USDT"), _sample_row(symbol="B/USDT", readiness_score=30)]
  out = tmp_path / "sqs.csv"
  save_sqs_ranked_csv(rows, out)
  assert out.exists()
  saved = list(csv.DictReader(out.open()))
  assert len(saved) == 2
  assert saved[0]["sqs_rank"] == "1"
  assert float(saved[0]["sqs_score"]) >= float(saved[1]["sqs_score"])


def test_non_primary_row_skipped():
  m = compute_setup_quality_score(_sample_row(row_type="contingent_scenario"))
  assert m["sqs_tier"] == "SKIP"
  assert m["sqs_score"] == 0


def test_invalid_geometry_is_hard_skip():
  m = compute_setup_quality_score(_sample_row(
    geometry_valid="N",
    geometry_errors="short_tp_not_descending",
  ))
  assert m["sqs_score"] == 0
  assert m["sqs_tier"] == "SKIP"
  assert m["sqs_action"] == "SKIP"


def test_negative_target_is_hard_skip_even_without_geometry_flag():
  m = compute_setup_quality_score(_sample_row(tp3=-1.0))
  assert m["sqs_score"] == 0
  assert m["sqs_tier"] == "SKIP"


def test_overall_history_cannot_produce_execute_tier():
  m = compute_setup_quality_score(_sample_row(
    hist_scope="overall",
    hist_win_rate=0.90,
    hist_n=1000,
  ))
  assert m["sqs_tier"] != "EXECUTE"


def test_watch_routing_caps_sqs_at_watch():
  m = compute_setup_quality_score(_sample_row(
    gtc_tier="watch",
    executive_action="WATCH_ONLY",
    readiness_score=100,
  ))
  assert m["sqs_tier"] == "WATCH"
  assert m["sqs_score"] < 60
