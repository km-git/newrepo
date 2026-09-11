"""Market-time helpers — never use wall clock for data windows or as-of stamps."""

from __future__ import annotations

import os
from datetime import datetime, timezone
from typing import Any, Dict, Mapping, Optional, Union

import pandas as pd

FrameLike = Union[pd.DataFrame, pd.Series, None]


def last_candle_ts_utc(df: FrameLike) -> Optional[datetime]:
  """Last closed candle timestamp from an OHLCV frame (UTC)."""
  if df is None or not hasattr(df, "index") or len(df) == 0:
    return None
  idx = df.index[-1]
  if isinstance(idx, pd.Timestamp):
    return idx.to_pydatetime().astimezone(timezone.utc)
  try:
    return pd.Timestamp(idx).to_pydatetime().astimezone(timezone.utc)
  except Exception:
    return None


def last_close_price(df: FrameLike) -> Optional[float]:
  if df is None or len(df) == 0:
    return None
  try:
    if "Close" in df.columns:
      return float(df["Close"].iloc[-1])
    return float(df.iloc[-1])
  except Exception:
    return None


def data_as_of_from_frames(
  frames: Mapping[str, FrameLike],
  *,
  prefer_tf: str = "1h",
) -> Optional[str]:
  """
  Canonical data-as-of UTC ISO string from exchange candle closes.
  Prefers prefer_tf, else latest across all frames.
  """
  if not frames:
    return None
  order = [prefer_tf] + [t for t in frames if t != prefer_tf]
  best: Optional[datetime] = None
  for tf in order:
    ts = last_candle_ts_utc(frames.get(tf))
    if ts is None:
      continue
    if best is None or ts > best:
      best = ts
  return best.isoformat() if best else None


def market_now_utc() -> datetime:
  """
  Reference 'now' for trading windows.
  Override with EW_MARKET_AS_OF_UTC (ISO) when VM wall clock is wrong.
  """
  raw = os.environ.get("EW_MARKET_AS_OF_UTC", "").strip()
  if raw:
    try:
      return datetime.fromisoformat(raw.replace("Z", "+00:00")).astimezone(timezone.utc)
    except ValueError:
      pass
  return datetime.now(timezone.utc)


def market_today_utc_date() -> str:
  return market_now_utc().strftime("%Y-%m-%d")


def data_as_of_meta(frames: Mapping[str, FrameLike]) -> Dict[str, Any]:
  """Per-TF last candle UTC + close for audit tables."""
  out: Dict[str, Any] = {}
  for tf, df in (frames or {}).items():
    ts = last_candle_ts_utc(df)
    out[tf] = {
      "last_candle_utc": ts.isoformat() if ts else None,
      "last_close": last_close_price(df),
    }
  out["canonical_as_of_utc"] = data_as_of_from_frames(frames)
  return out
