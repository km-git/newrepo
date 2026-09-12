"""Closed-bar policy — no forming-candle leakage."""

from __future__ import annotations

import os
from datetime import datetime, timedelta, timezone

import pandas as pd

from core.market_clock import drop_forming_bar, is_bar_closed


def _ohlcv_at(ts: datetime, close: float = 100.0) -> pd.DataFrame:
  idx = pd.DatetimeIndex([ts], tz="UTC")
  return pd.DataFrame(
    {"Open": close, "High": close + 1, "Low": close - 1, "Close": close, "Volume": 1.0},
    index=idx,
  )


def test_drop_forming_bar_removes_open_candle():
  now = datetime(2026, 9, 11, 22, 30, tzinfo=timezone.utc)
  open_ts = datetime(2026, 9, 11, 22, 0, tzinfo=timezone.utc)  # 1h bar still forming
  df = _ohlcv_at(open_ts)
  os.environ["EW_MARKET_AS_OF_UTC"] = now.isoformat()
  try:
    out = drop_forming_bar(df, "1h")
    assert len(out) == 0
    assert not is_bar_closed(open_ts, "1h", now=now)
  finally:
    os.environ.pop("EW_MARKET_AS_OF_UTC", None)


def test_drop_forming_bar_keeps_closed_candle():
  now = datetime(2026, 9, 11, 22, 30, tzinfo=timezone.utc)
  closed_ts = datetime(2026, 9, 11, 21, 0, tzinfo=timezone.utc)
  df = _ohlcv_at(closed_ts)
  os.environ["EW_MARKET_AS_OF_UTC"] = now.isoformat()
  try:
    out = drop_forming_bar(df, "1h")
    assert len(out) == 1
    assert is_bar_closed(closed_ts, "1h", now=now)
  finally:
    os.environ.pop("EW_MARKET_AS_OF_UTC", None)
