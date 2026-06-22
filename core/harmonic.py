"""Harmonic XABCD — full scan + kill-zone / price-proximity tagging."""

from __future__ import annotations

from typing import List, Optional, Tuple

import pandas as pd
from pyharmonics.search import HarmonicSearch
from pyharmonics.technicals import OHLCTechnicals

from cache.dedup import dedup_harmonics
from cache.disk_cache import get_cache

XABCD_PATTERNS = {"GARTLEY", "BAT", "BUTTERFLY", "CRAB", "CYPHER", "SHARK", "XABCD"}


def _search_patterns(df: pd.DataFrame, tf: str, symbol: str) -> List[dict]:
  pdf = df[["Open", "High", "Low", "Close", "Volume"]].copy()
  pdf.columns = ["open", "high", "low", "close", "volume"]
  t = OHLCTechnicals(pdf, symbol, tf, peak_spacing=8)
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
      retraces = getattr(p, "retraces", {}) or {}
      out.append(
        {
          "tf": tf,
          "pattern": name,
          "prz_low": prz_low,
          "prz_high": prz_high,
          "prz_mid": (prz_low + prz_high) / 2,
          "ratios": {k: round(float(v), 4) for k, v in retraces.items()},
          "bullish": getattr(p, "bullish", True),
        }
      )
  return dedup_harmonics(out)


def scan_harmonics(
  df: pd.DataFrame,
  tf: str,
  symbol: str,
  current_price: float,
  kill_zone: Optional[Tuple[float, float]] = None,
) -> dict:
  """Return all harmonics on TF + flags for kill-zone and price proximity."""
  cache = get_cache()
  kz = kill_zone or (0.0, 0.0)

  def _compute():
    patterns = _search_patterns(df, tf, symbol)
    enriched = []
    for p in patterns:
      prz_mid = p["prz_mid"]
      dist_pct = abs(prz_mid - current_price) / current_price * 100
      in_kz = False
      if kill_zone:
        kz_low, kz_high = kill_zone
        in_kz = (p["prz_low"] <= kz_high) and (p["prz_high"] >= kz_low)
      near_price = dist_pct <= 3.0
      enriched.append({**p, "dist_from_price_pct": round(dist_pct, 2), "in_kill_zone": in_kz, "near_price": near_price})
    enriched.sort(key=lambda x: x["dist_from_price_pct"])
    return {
      "tf": tf,
      "count": len(enriched),
      "patterns": enriched,
      "in_zone": [p for p in enriched if p["in_kill_zone"]],
      "near_price": [p for p in enriched if p["near_price"]],
    }

  result, hit = cache.get_or_compute(
    "harmonics_v2",
    _compute,
    symbol,
    tf,
    round(kz[0], 2),
    round(kz[1], 2),
    len(df),
    round(current_price, 2),
  )
  if hit:
    print(f"[cache] HIT harmonics_v2 {symbol} {tf}")
  return result


def detect_harmonics(
  df: pd.DataFrame, tf: str, kill_zone: Tuple[float, float], symbol: str = "SYMBOL"
) -> List[dict]:
  """Backward-compatible: patterns overlapping kill zone."""
  current = float(df["Close"].iloc[-1])
  scan = scan_harmonics(df, tf, symbol, current, kill_zone)
  return scan["in_zone"]


def collect_actionable_harmonics(
  scans: List[dict], prefer_near_price: bool = True
) -> List[dict]:
  """Merge scans; prefer in-zone, else near-price patterns."""
  out: List[dict] = []
  seen = set()
  for scan in scans:
    pool = scan["in_zone"] if scan["in_zone"] else (scan["near_price"] if prefer_near_price else scan["patterns"][:3])
    for p in pool:
      key = (p["tf"], p["pattern"], round(p["prz_low"], 2))
      if key not in seen:
        seen.add(key)
        out.append(p)
  return out
