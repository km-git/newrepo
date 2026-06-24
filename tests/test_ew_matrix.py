"""Tests for guaranteed EW matrix coverage."""

from __future__ import annotations

from engine.ew_matrix import build_ew_matrix, ew_coverage_summary


def test_ew_matrix_all_tfs_present():
  tfs = ["1w", "1d", "4h", "1h", "15m"]
  adaptive = {
    "1d": {"monowaves": [
      {"type": "Up", "price_start": 100, "price_end": 110},
      {"type": "Down", "price_start": 110, "price_end": 105},
      {"type": "Up", "price_start": 105, "price_end": 115},
    ], "skip": 3, "bars": 100, "status": "ok"},
  }
  data = {"1d": __import__("pandas").DataFrame({
    "Open": [100] * 20, "High": [110] * 20, "Low": [95] * 20, "Close": [105] * 20, "Volume": [1000] * 20,
  })}
  matrix = build_ew_matrix(adaptive, data, tfs)
  assert len(matrix) == 5
  assert matrix["1d"]["status"] == "ok"
  assert matrix["15m"]["status"] == "not_requested"
  summary = ew_coverage_summary(matrix, tfs)
  assert summary["timeframes_analyzed"] == 1
  assert "15m" in summary["structures_by_tf"]
