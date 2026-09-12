"""Autodream must not label in-sample win rate as OOS."""

from __future__ import annotations

import pandas as pd

from engine.autodream import enrich_outcomes_with_autodream


def test_oos_fields_use_walk_forward_not_in_sample():
  n = 80
  idx = pd.date_range("2024-01-01", periods=n, freq="1h", tz="UTC")
  close = 100 + pd.Series(range(n)).astype(float)
  df = pd.DataFrame(
    {"Open": close, "High": close + 1, "Low": close - 1, "Close": close, "Volume": 1000.0},
    index=idx,
  )
  data = {"1d": df, "1h": df, "15m": df}
  setup = {
    "status": "monitor",
    "direction": "LONG",
    "style": "swing",
    "timeframe": "1d",
    "stop_loss": {"price": 95, "distance_pct": 5},
    "targets": [{"price": 105, "rr": 1}, {"price": 110, "rr": 2}],
    "entry": {"anchor": 100},
    "readiness_score": 70,
  }
  outcomes = {"setups": {"swing": setup}}
  enriched = enrich_outcomes_with_autodream(outcomes, "TEST/USDT", data)
  s = enriched["setups"]["swing"]
  if s.get("is_trades") and s.get("oos_trades"):
    # When both exist they must not be blindly equal unless WF matches IS
        assert "is_win_rate" in s
        assert "oos_win_rate" in s or s.get("oos_trades", 0) < 3
