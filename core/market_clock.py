"""Market-time helpers — never use wall clock for data windows or as-of stamps."""

from __future__ import annotations

import os
from datetime import datetime, timedelta, timezone
from typing import Any, Dict, Iterable, Mapping, Optional, Union

import pandas as pd

FrameLike = Union[pd.DataFrame, pd.Series, None]

TF_BAR_SECONDS: Dict[str, int] = {
  "15m": 900,
  "1h": 3600,
  "4h": 14_400,
  "12h": 43_200,
  "1d": 86_400,
  "1w": 604_800,
}


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


def bar_duration_seconds(timeframe: str) -> int:
  return TF_BAR_SECONDS.get(timeframe, 3600)


def is_bar_closed(bar_open_ts: datetime, timeframe: str, *, now: Optional[datetime] = None) -> bool:
  """True when the candle period [open, open+duration) has ended."""
  ref = now or market_now_utc()
  return ref >= bar_open_ts + timedelta(seconds=bar_duration_seconds(timeframe))


def drop_forming_bar(df: FrameLike, timeframe: str) -> FrameLike:
  """
  Remove the last row when its candle is still forming.
  All features/indicators must run on closed bars only.
  """
  if df is None or not hasattr(df, "index") or len(df) == 0:
    return df
  last_ts = last_candle_ts_utc(df)
  if last_ts is None:
    return df
  if is_bar_closed(last_ts, timeframe):
    return df
  trimmed = df.iloc[:-1]
  return trimmed.copy() if hasattr(trimmed, "copy") else trimmed


def drop_forming_bars(frames: Mapping[str, FrameLike]) -> Dict[str, FrameLike]:
  return {tf: drop_forming_bar(df, tf) for tf, df in (frames or {}).items()}


def series_fingerprint(df: FrameLike, n: int = 20) -> tuple:
  """Tail-close fingerprint for cache keys (mirror- and scale-aware)."""
  if df is None or len(df) == 0:
    return ()
  tail = df["Close"].iloc[-n:].astype(float).values if hasattr(df, "columns") else df.iloc[-n:]
  return tuple(round(float(x), 6) for x in tail)


def frames_fingerprint(frames: Mapping[str, FrameLike], tfs: Optional[Iterable[str]] = None) -> tuple:
  """Multi-TF fingerprint for cache keys (mirror-symmetric)."""
  keys = sorted(tfs or frames.keys())
  out: list = []
  for tf in keys:
    df = (frames or {}).get(tf)
    if df is not None and len(df) > 0:
      out.append((tf, series_fingerprint(df)))
  return tuple(out)


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
