"""Semantic cache for repetitive OHLCV queries (Cloudflare AI Gateway pattern).

Exact-key disk cache (CompressedCache) misses when limit differs slightly or the
same symbol/tf is re-queried within a candle window. Semantic cache matches on
normalized (symbol, timeframe, exchange) and serves a superset of bars.
"""

from __future__ import annotations

import hashlib
import json
import time
from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional, Tuple

import pandas as pd

from cache.disk_cache import CompressedCache, get_cache

# TTL seconds per timeframe — aligned to candle cadence
TF_TTL_SECONDS: Dict[str, int] = {
  "1w": 86_400,
  "1d": 3_600,
  "4h": 900,
  "1h": 300,
  "15m": 60,
}

NAMESPACE = "semantic_ohlcv"


def normalize_symbol(symbol: str) -> str:
  """BTC/USDT, BTCUSDT, btc-usdt → BTC/USDT."""
  s = symbol.upper().replace("-", "/").replace("_", "/")
  if "/" not in s and s.endswith("USDT"):
    return f"{s[:-4]}/USDT"
  if "/" not in s and len(s) > 4:
    return f"{s[:-4]}/{s[-4:]}"
  return s


def semantic_key(symbol: str, timeframe: str, exchange_chain: Tuple[str, ...]) -> str:
  payload = json.dumps(
    [normalize_symbol(symbol), timeframe, list(exchange_chain)],
    sort_keys=True,
  )
  return hashlib.sha256(payload.encode()).hexdigest()[:24]


@dataclass
class SemanticCacheEntry:
  symbol: str
  timeframe: str
  exchange: str
  limit_fetched: int
  fetched_at: float
  df: pd.DataFrame

  def is_fresh(self, timeframe: str) -> bool:
    ttl = TF_TTL_SECONDS.get(timeframe, 300)
    return (time.time() - self.fetched_at) < ttl

  def can_serve(self, requested_limit: int) -> bool:
    # Exchanges may return fewer bars than requested (e.g. 1d cap 300); serve if fresh.
    return len(self.df) > 0 and self.is_fresh(self.timeframe)

  def slice_for(self, requested_limit: int) -> pd.DataFrame:
    if len(self.df) <= requested_limit:
      return self.df.copy()
    return self.df.iloc[-requested_limit:].copy()


@dataclass
class SemanticCacheStats:
  exact_hits: int = 0
  semantic_hits: int = 0
  misses: int = 0
  bytes_saved_estimate: int = 0

  def to_dict(self) -> dict:
    total = self.exact_hits + self.semantic_hits + self.misses
    hit_rate = (
      round(100 * (self.exact_hits + self.semantic_hits) / total, 1) if total else 0.0
    )
    return {
      "exact_hits": self.exact_hits,
      "semantic_hits": self.semantic_hits,
      "misses": self.misses,
      "hit_rate_pct": hit_rate,
      "bytes_saved_estimate": self.bytes_saved_estimate,
    }


class SemanticOHLCVCache:
  """In-memory index over disk blobs for semantic OHLCV reuse."""

  def __init__(self, disk: Optional[CompressedCache] = None):
    self._disk = disk or get_cache()
    self._index: Dict[str, SemanticCacheEntry] = {}
    self.stats = SemanticCacheStats()

  def _disk_key(self, sem_key: str, limit: int) -> str:
    return f"{sem_key}:{limit}"

  def get(
    self,
    symbol: str,
    timeframe: str,
    limit: int,
    exchange_chain: Tuple[str, ...],
  ) -> Tuple[Optional[pd.DataFrame], str]:
    """
    Return (dataframe, hit_type).
    hit_type: 'exact' | 'semantic' | 'miss'
    """
    sem = semantic_key(symbol, timeframe, exchange_chain)
    exact_disk_key = self._disk_key(sem, limit)

    # Exact hit from disk
    blob = self._disk.get(NAMESPACE, exact_disk_key)
    if blob is not None:
      entry = SemanticCacheEntry(**blob)
      if entry.can_serve(limit):
        self.stats.exact_hits += 1
        self._index[sem] = entry
        return entry.slice_for(limit), "exact"

    # Semantic hit: any cached entry with same sem key and limit >= requested
    mem = self._index.get(sem)
    if mem and mem.can_serve(limit):
      self.stats.semantic_hits += 1
      est = len(mem.df) * 48  # rough bytes per OHLCV row
      self.stats.bytes_saved_estimate += est
      return mem.slice_for(limit), "semantic"

    # Scan disk for any cached bar count under this semantic key
    for stored_limit in (500, 480, 300, 200, 100):
      blob = self._disk.get(NAMESPACE, self._disk_key(sem, stored_limit))
      if blob is None:
        continue
      entry = SemanticCacheEntry(**blob)
      if entry.can_serve(limit):
        self.stats.semantic_hits += 1
        self._index[sem] = entry
        self.stats.bytes_saved_estimate += len(entry.df) * 48
        return entry.slice_for(limit), "semantic"

    self.stats.misses += 1
    return None, "miss"

  def put(
    self,
    symbol: str,
    timeframe: str,
    limit: int,
    exchange_chain: Tuple[str, ...],
    exchange: str,
    df: pd.DataFrame,
  ) -> None:
    sem = semantic_key(symbol, timeframe, exchange_chain)
    entry = SemanticCacheEntry(
      symbol=normalize_symbol(symbol),
      timeframe=timeframe,
      exchange=exchange,
      limit_fetched=len(df),
      fetched_at=time.time(),
      df=df,
    )
    self._index[sem] = entry
    self._disk.set(
      NAMESPACE,
      {
        "symbol": entry.symbol,
        "timeframe": entry.timeframe,
        "exchange": entry.exchange,
        "limit_fetched": entry.limit_fetched,
        "fetched_at": entry.fetched_at,
        "df": entry.df,
      },
      self._disk_key(sem, limit),
    )
