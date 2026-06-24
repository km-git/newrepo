"""Tests for indicator confluence and readiness resolution."""

from __future__ import annotations

import pandas as pd

from core.indicators import score_indicator_confluence, zone_proximity_pct
from engine.readiness import resolve_execution_status


def _df(n=60, trend=1.0):
  rows = []
  p = 100.0
  for i in range(n):
    p += trend * (0.5 if i % 3 else -0.2)
    rows.append({"Open": p, "High": p + 1, "Low": p - 1, "Close": p, "Volume": 1000 + i * 10})
  return pd.DataFrame(rows)


def test_zone_proximity_inside():
  assert zone_proximity_pct(100, 99, 101) == 0.0


def test_indicator_score_long():
  df = _df(80, trend=0.3)
  r = score_indicator_confluence(df, "LONG", 99, 101, "swing")
  assert "score" in r
  assert r["score"] >= 0


def test_probe_executable_via_indicators():
  status, tier, reason = resolve_execution_status(
    style="swing",
    direction="LONG",
    wave={"structure": "abc_correction", "impulse_valid": False},
    in_zone=False,
    zone_dist_pct=1.2,
    impulse_valid=False,
    consensus_dir="BULL",
    rr=2.0,
    min_rr=1.5,
    harmonic_near=True,
    indicator={"score": 72, "aligned": True, "signals": ["near zone", "RSI 48"], "threshold": 55},
    executive_verdict="STAGED_GO",
  )
  assert status == "executable"
  assert tier == "probe"
  assert "PROBE" in reason
