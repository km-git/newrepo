"""Cloudflare AI Gateway–style layer for live Bybit/Binance OHLCV fetches.

- Routes to preferred exchange (bybit, binance) with fallback chain
- Semantic cache before hitting the exchange API
- Request log with latency + cache hit type (token-efficient agent traces)
"""

from __future__ import annotations

import json
import time
from dataclasses import dataclass, field
from typing import Any, Callable, Dict, List, Optional, Tuple

import pandas as pd

from cache.semantic_cache import SemanticOHLCVCache, normalize_symbol

DEFAULT_CHAIN = ("okx", "bybit", "kraken", "binance")
LIVE_CHAIN_BYBIT_FIRST = ("bybit", "binance", "okx", "kraken")
LIVE_CHAIN_BINANCE_FIRST = ("binance", "bybit", "okx", "kraken")


@dataclass
class GatewayRequest:
  symbol: str
  timeframes: List[str]
  limit: int
  exchange_chain: Tuple[str, ...]
  timestamp: float = field(default_factory=time.time)


@dataclass
class GatewayResponse:
  data: Dict[str, pd.DataFrame]
  exchange_used: str
  cache_hits: Dict[str, str]  # tf -> exact|semantic|miss
  latency_ms: float
  requests_log: List[dict] = field(default_factory=list)


class MarketDataGateway:
  """
  Gateway in front of ccxt live fetches.

  Mirrors Cloudflare AI Gateway responsibilities:
  - cache (semantic + exact)
  - routing (exchange preference)
  - observability (per-request log)
  """

  def __init__(
    self,
    semantic_cache: Optional[SemanticOHLCVCache] = None,
    fetch_fn: Optional[Callable[..., Dict[str, pd.DataFrame]]] = None,
  ):
    self._cache = semantic_cache or SemanticOHLCVCache()
    self._fetch_fn = fetch_fn
    self._request_log: List[dict] = []

  @staticmethod
  def chain_for_preference(preference: Optional[str]) -> Tuple[str, ...]:
    pref = (preference or "").lower().strip()
    if pref == "bybit":
      return LIVE_CHAIN_BYBIT_FIRST
    if pref == "binance":
      return LIVE_CHAIN_BINANCE_FIRST
    if pref in LIVE_CHAIN_BYBIT_FIRST:
      return (pref,) + tuple(x for x in DEFAULT_CHAIN if x != pref)
    return DEFAULT_CHAIN

  def fetch_ohlcv(
    self,
    symbol: str,
    timeframes: List[str],
    limit: int = 500,
    exchange_preference: Optional[str] = None,
  ) -> GatewayResponse:
    chain = self.chain_for_preference(exchange_preference)
    sym = normalize_symbol(symbol)
    t0 = time.time()
    cache_hits: Dict[str, str] = {}
    out: Dict[str, pd.DataFrame] = {}
    missing_tfs: List[str] = []

    for tf in timeframes:
      df, hit = self._cache.get(sym, tf, limit, chain)
      cache_hits[tf] = hit
      if df is not None:
        out[tf] = df
        self._log_request(sym, tf, limit, chain, hit, 0.0, source="cache")
      else:
        missing_tfs.append(tf)

    exchange_used = "cache-only"
    if missing_tfs:
      if self._fetch_fn is None:
        from fetchers.ccxt_fetcher import _fetch_ohlcv_crypto_uncached

        raw = _fetch_ohlcv_crypto_uncached(sym, missing_tfs, limit, chain)
      else:
        raw = self._fetch_fn(sym, missing_tfs, limit, chain)

      for tf in missing_tfs:
        if tf not in raw:
          continue
        out[tf] = raw[tf]
        cache_hits[tf] = "miss"
        # Infer exchange from fetch logs is hard; store chain head as label
        exchange_used = chain[0]
        self._cache.put(sym, tf, limit, chain, exchange_used, raw[tf])
        self._log_request(sym, tf, limit, chain, "miss", 0.0, source=exchange_used)

    latency_ms = round((time.time() - t0) * 1000, 2)
    return GatewayResponse(
      data=out,
      exchange_used=exchange_used,
      cache_hits=cache_hits,
      latency_ms=latency_ms,
      requests_log=list(self._request_log[-len(timeframes) :]),
    )

  def _log_request(
    self,
    symbol: str,
    tf: str,
    limit: int,
    chain: Tuple[str, ...],
    hit: str,
    latency_ms: float,
    source: str,
  ) -> None:
    entry = {
      "gateway": "market_data",
      "symbol": symbol,
      "timeframe": tf,
      "limit": limit,
      "exchange_chain": list(chain),
      "cache_hit": hit,
      "source": source,
      "latency_ms": latency_ms,
      "ts": time.time(),
    }
    self._request_log.append(entry)
    if hit == "miss":
      print(f"[gateway] MISS {symbol} {tf} → live via {source}")
    else:
      print(f"[gateway] {hit.upper()} {symbol} {tf} (saved live fetch)")

  def stats(self) -> dict:
    sem = self._cache.stats.to_dict()
    return {
      "semantic_cache": sem,
      "requests_logged": len(self._request_log),
      "recent": self._request_log[-5:],
    }

  def compact_log_for_agent(self, max_entries: int = 10) -> str:
    """Minified JSON log for agent context (RepoMix / gateway observability)."""
    payload = self._request_log[-max_entries:]
    return json.dumps(payload, separators=(",", ":"), default=str)


_gateway: Optional[MarketDataGateway] = None


def get_gateway() -> MarketDataGateway:
  global _gateway
  if _gateway is None:
    _gateway = MarketDataGateway()
  return _gateway
