"""Harmonic XABCD overlay (5-point patterns only)."""

from __future__ import annotations

from typing import List, Tuple

import pandas as pd
from pyharmonics.search import HarmonicSearch
from pyharmonics.technicals import OHLCTechnicals

from cache.dedup import dedup_harmonics
from cache.disk_cache import get_cache

XABCD_PATTERNS = {"GARTLEY", "BAT", "BUTTERFLY", "CRAB", "CYPHER", "SHARK", "XABCD"}


def detect_harmonics(df: pd.DataFrame, tf: str, kill_zone: Tuple[float, float], symbol: str = "SYMBOL") -> List[dict]:
  cache = get_cache()
  kz_low, kz_high = kill_zone
  last_close = float(df["Close"].iloc[-1])

  def _search():
    pdf = df[["Open", "High", "Low", "Close", "Volume"]].copy()
    pdf.columns = ["open", "high", "low", "close", "volume"]
    t = OHLCTechnicals(pdf, symbol, tf, peak_spacing=10)
    hs = HarmonicSearch(t)
    hs.search()
    out: List[dict] = []
    for name, plist in hs.get_patterns().items():
      if name.upper() not in XABCD_PATTERNS:
        continue
      for p in plist:
        v1 = getattr(p, "completion_min_price", None)
        v2 = getattr(p, "completion_max_price", None)
        if v1 is None or v2 is None:
          continue
        prz_low, prz_high = float(min(v1, v2)), float(max(v1, v2))
        overlap = (prz_low <= kz_high) and (prz_high >= kz_low)
        if overlap:
          retraces = getattr(p, "retraces", {}) or {}
          out.append(
            {
              "tf": tf,
              "pattern": name,
              "prz_low": prz_low,
              "prz_high": prz_high,
              "ratios": {k: float(v) for k, v in retraces.items()},
              "bullish": getattr(p, "bullish", True),
            }
          )
    return dedup_harmonics(out)

  result, hit = cache.get_or_compute(
    "harmonics",
    _search,
    symbol,
    tf,
    round(kz_low, 2),
    round(kz_high, 2),
    len(df),
    round(last_close, 2),
  )
  if hit:
    print(f"[cache] HIT harmonics {symbol} {tf}")
  return result
